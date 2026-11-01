"""Orbitoby three-source physical metadata archive.

Official interfaces: GCAT TSV; ESA DISCOSweb API v2; KeepTrack v4 bulk brief.
Preserves every field in raw documents, and extracts only explicitly identified
physical metadata. No automatic mass/area/Cd/B* substitution or guessing.

Stdlib-only optional package module, safe to import without network access.
"""
from __future__ import annotations

import csv
import gzip
import hashlib
import io
import json
import os
import re
import sqlite3
from datetime import UTC as UTC_TZ
from datetime import datetime
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import urlencode, urlparse
from urllib.request import Request, urlopen

GCAT_BASE = 'https://planet4589.org/space/gcat/tsv/cat/'
DISCOS_BASE = 'https://discosweb.esoc.esa.int/api/objects'
KEEPTRACK_BULK = 'https://api.keeptrack.space/v4/sats/brief'
KEEPTRACK_TERMS = 'https://api.keeptrack.space/v4/docs'
GCAT_DEFAULT = ('satcat', 'satcat100k', 'psatcat', 'psatcat100k')
GCAT_FULL = (
    'satcat', 'satcat100k', 'auxcat', 'ftocat', 'tmpcat', 'csocat',
    'satcat070k', 'satcat270k', 'satcat700M', 'vimcat', 'lcat', 'rcat',
    'deepcat', 'ecat', 'hcocat', 'lprcat', 'psatcat', 'psatcat100k', 'pauxcat', 'pftocat', 'ptmpcat',
    'plcat', 'prcat', 'pdeepcat',
)
UTC = lambda: datetime.now(UTC_TZ).isoformat()


class ArchiveError(RuntimeError):
    pass


class RateLimited(ArchiveError):
    pass


def _positive(value):
    if isinstance(value, bool):
        return None
    try:
        number = float(str(value).strip().replace(',', ''))
        if 0 < number < 1e15:
            return number
    except (ValueError, TypeError):
        pass
    return None


def _norad(value):
    if isinstance(value, bool):
        return None
    txt = str(value).strip()
    return int(txt) if re.fullmatch(r'\d{1,9}', txt) and int(txt) > 0 else None


def _key_get(obj, *aliases):
    if not isinstance(obj, dict):
        return None
    lookup = {str(k).casefold().replace('_', ''): k for k in obj}
    for alias in aliases:
        found = lookup.get(alias.casefold().replace('_', ''))
        if found is not None:
            return obj[found]
    return None


def _safe_text(value):
    if value is None or (isinstance(value, str) and value.strip() in ('', '-', '?', '--')):
        return None
    return str(value)


def _keeptrack_norad(obj):
    """NORAD from explicitly named fields, or matching 5-digit TLE line IDs.

    The generic JSON key `id` is not trusted as a NORAD identifier unless
    its value matches an actual pair of TLE catalog numbers.
    """
    n=_norad(_key_get(obj,'SCC_NUM','sccNum','NORAD_CAT_ID','NORAD_ID',
                       'noradId','norad','satnum','satno','catalogNumber','catalogId'))
    if n is not None:
        return n
    one=_key_get(obj,'tle1','TLE_LINE_1')
    two=_key_get(obj,'tle2','TLE_LINE_2')
    if (isinstance(one, str) and isinstance(two, str) and one.startswith('1 ')
            and two.startswith('2 ') and len(one) >= 7 and len(two) >= 7):
            part1,part2=one[2:7].strip(),two[2:7].strip()
            if part1==part2 and part1.isdecimal():
                n=int(part1)
                internal=_norad(_key_get(obj,'id'))
                if internal is not None and internal != n:
                    # Identity conflict: source 'id' may be an internal key.
                    return n
                return n
    return None


def _records_from_bulk(body):
    if isinstance(body, list):
        return body
    if isinstance(body, dict):
        for field in ('data', 'satellites', 'objects', 'sats', 'results'):
            if isinstance(body.get(field), list):
                return body[field]
    raise ArchiveError('Unexpected KeepTrack bulk response shape; no records imported')


def _raw_request(url, headers, *, timeout=60, max_bytes=160_000_000):
    parsed = urlparse(url)
    if parsed.scheme != 'https':
        raise ArchiveError('Only HTTPS sources are allowed')
    req = Request(url, headers=headers)
    try:
        with urlopen(req, timeout=timeout) as r:
            status = getattr(r, 'status', 200)
            response_headers = dict(r.headers.items())
            raw = b'' if status == 304 else r.read(max_bytes + 1)
    except HTTPError as exc:
        if exc.code in (401, 403):
            raise ArchiveError(f'Authentication / permission denied: HTTP {exc.code} at {parsed.netloc}') from None
        if exc.code == 429:
            raise RateLimited(f'Rate limit HTTP 429 at {parsed.netloc}; check Retry-After, resume later') from None
        raise ArchiveError(f'HTTP {exc.code} at {parsed.netloc}') from None
    if len(raw) > max_bytes:
        raise ArchiveError(f'Response larger than {max_bytes} bytes')
    if not raw and status != 304:
        raise ArchiveError('Empty response')
    return status, response_headers, raw


class PhysicalArchive:
    """Local queryable provenance database; use `PhysicalArchive.open(path)`.

    All records remain separately attributed to GCAT, DISCOS and KeepTrack.
    No provider is silently preferred. `get(norad)` exposes all raw records.
    """

    def __init__(self, path):
        self.path = Path(path).expanduser().resolve()
        self.path.mkdir(parents=True, exist_ok=True)
        self.con = sqlite3.connect(self.path / 'physical_archives.sqlite3')
        self.con.row_factory = sqlite3.Row
        self.con.executescript('''
        PRAGMA journal_mode=WAL;
        CREATE TABLE IF NOT EXISTS records (
          provider TEXT NOT NULL, source_key TEXT NOT NULL,
          norad_id INTEGER, jcat TEXT, source_group TEXT NOT NULL,
          raw_json TEXT NOT NULL, source_url TEXT NOT NULL,
          retrieved_utc TEXT NOT NULL, PRIMARY KEY(provider, source_key));
        CREATE INDEX IF NOT EXISTS ix_record_norad ON records(norad_id);
        CREATE INDEX IF NOT EXISTS ix_record_jcat ON records(jcat);
        CREATE TABLE IF NOT EXISTS properties (
          provider TEXT NOT NULL, source_key TEXT NOT NULL, norad_id INTEGER,
          field TEXT NOT NULL, value_numeric REAL, value_text TEXT, unit TEXT,
          source_field TEXT NOT NULL, caveat TEXT NOT NULL,
          PRIMARY KEY(provider, source_key, field));
        CREATE INDEX IF NOT EXISTS ix_property_norad ON properties(norad_id,field);
        CREATE TABLE IF NOT EXISTS receipts (
          id INTEGER PRIMARY KEY AUTOINCREMENT, provider TEXT NOT NULL,
          source_group TEXT NOT NULL, source_url TEXT NOT NULL,
          sha256 TEXT NOT NULL, rows INTEGER NOT NULL, retrieved_utc TEXT NOT NULL,
          snapshot_path TEXT NOT NULL, scope TEXT NOT NULL);
        CREATE TABLE IF NOT EXISTS state (
          provider TEXT NOT NULL, job TEXT NOT NULL,
          cursor TEXT, complete INTEGER NOT NULL DEFAULT 0,
          requests INTEGER NOT NULL DEFAULT 0, last_error TEXT,
          PRIMARY KEY(provider,job));
        ''')
        self.con.commit()

    @classmethod
    def open(cls, path=None):
        return cls(path or os.environ.get('ORBITOBY_PHYSICS_DIR', '~/Desktop/Orbitoby_Physical_Archives'))

    def close(self):
        self.con.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _store_snapshot(self, provider, group, url, raw, *, scope):
        digest = hashlib.sha256(raw).hexdigest()
        folder = self.path / 'snapshots' / provider
        folder.mkdir(parents=True, exist_ok=True)
        snap = folder / (re.sub('[^A-Za-z0-9_.-]', '_', group) + '_' + digest[:16] + '.gz')
        if not snap.exists():
            with gzip.open(snap, 'wb') as f:
                f.write(raw)
        return digest, str(snap)

    def _record(self, provider, source_key, norad_id, jcat, group, obj, source_url, fields):
        self.con.execute('''INSERT OR REPLACE INTO records VALUES (?,?,?,?,?,?,?,?)''',
                         (provider, source_key, norad_id, jcat, group,
                          json.dumps(obj, ensure_ascii=False, default=str), source_url, UTC()))
        self.con.execute('DELETE FROM properties WHERE provider=? AND source_key=?', (provider, source_key))
        for field, raw_val, unit, source_field, caveat in fields:
            n = _positive(raw_val) if unit in ('kg', 'm', 'm2', 'kg/m2', '1', 'W') else None
            txt = str(raw_val).strip() if field.endswith('_flag') and raw_val is not None else _safe_text(raw_val)
            if txt is None or txt == '':
                continue
            self.con.execute('''INSERT OR REPLACE INTO properties VALUES (?,?,?,?,?,?,?,?,?)''',
                             (provider, source_key, norad_id, field, n, txt, unit, source_field, caveat))

    def _receipt(self, provider, group, url, raw, rows, scope):
        digest, snap = self._store_snapshot(provider, group, url, raw, scope=scope)
        self.con.execute('''INSERT INTO receipts(provider,source_group,source_url,sha256,rows,retrieved_utc,snapshot_path,scope)
                            VALUES(?,?,?,?,?,?,?,?)''', (provider, group, url, digest, rows, UTC(), snap, scope))

    def _update_state(self, provider, job, cursor=None, *, complete=False, increment=0, error=None):
        current = self.con.execute('SELECT requests FROM state WHERE provider=? AND job=?', (provider,job)).fetchone()
        total = (current['requests'] if current else 0) + increment
        self.con.execute('''INSERT OR REPLACE INTO state VALUES(?,?,?,?,?,?)''',
                         (provider, job, cursor, int(complete), total, error))
        self.con.commit()

    def _get_state(self, provider, job):
        row = self.con.execute('SELECT * FROM state WHERE provider=? AND job=?',(provider,job)).fetchone()
        return dict(row) if row else None

    def import_gcat_tsv(self, filename, raw: bytes, url='local:GCAT-import'):
        """Import an official GCAT TSV while preserving every column, including qualifiers.

        GCAT payload catalog records without numeric Satcat are linked by JCAT
        after object catalogs have been imported. Ambiguous JCAT links stay NULL.
        """
        name = Path(filename).stem
        if name not in GCAT_FULL:
            raise ValueError(f'Unrecognized GCAT catalog name {name}')
        lines = raw.decode('utf-8-sig', errors='replace').splitlines()
        head = next((i for i,x in enumerate(lines) if x.startswith(('#JCAT\t', 'JCAT\t'))),None)
        if head is None:
            raise ArchiveError('No GCAT TSV JCAT header')
        content = [lines[head].lstrip('#')] + [x for x in lines[head+1:] if x.strip() and not x.startswith('#')]
        reader = csv.DictReader(io.StringIO('\n'.join(content)), delimiter='\t')
        # Replacements of the same official file must not retain obsolete rows.
        self.con.execute("DELETE FROM properties WHERE provider='gcat' AND source_key IN "
                         "(SELECT source_key FROM records WHERE provider='gcat' AND source_group=?)", (name,))
        self.con.execute("DELETE FROM records WHERE provider='gcat' AND source_group=?", (name,))
        count=0
        for i,obj in enumerate(reader):
            jcat = (_key_get(obj,'JCAT') or '').strip()
            if not jcat:
                continue
            norad = _norad(_key_get(obj,'Satcat'))
            source_key = f'{name}:{jcat}:{i}'  # preserve phases/duplicate records
            field_specs = (
                ('launch_mass_kg','Mass','kg','Launch/catalog mass; quality flag separately preserved'),
                ('dry_mass_kg','DryMass','kg','Dry mass; not time-varying operational mass'),
                ('body_length_m','Length','m','Body dimension; not deployed drag area'),
                ('body_diameter_m','Diameter','m','Body dimension'),
                ('body_span_m','Span','m','May include appendages; not drag area'),
                ('shape','Shape',None,'Descriptive geometry only'),
                ('object_type','Type',None,'GCAT catalog object class'),
                ('mass_flag','MassFlag',None,'Source estimated/quality marker'),
                ('dry_mass_flag','DryFlag',None,'Source estimated/quality marker'),
            )
            fields=[]
            for dest,src,unit,note in field_specs:
                val=_key_get(obj,src)
                if val is not None:
                    fields.append((dest,val,unit,src,note))
            self._record('gcat',source_key,norad,jcat,name,obj,url,fields)
            count+=1
        self._receipt('gcat',name,url,raw,count,'GCAT catalog '+name)
        self.con.commit()
        self.resolve_gcat_jcat()
        return count

    def resolve_gcat_jcat(self):
        """Fill matching payload JCAT IDs only where linked object's NORAD ID is unambiguous."""
        self.con.execute('''UPDATE records SET norad_id=(
          SELECT MIN(b.norad_id) FROM records b WHERE b.provider='gcat'
          AND b.jcat=records.jcat AND b.norad_id IS NOT NULL
          HAVING COUNT(DISTINCT b.norad_id)=1)
          WHERE provider='gcat' AND norad_id IS NULL AND jcat IS NOT NULL AND EXISTS (
          SELECT 1 FROM records b WHERE b.provider='gcat' AND b.jcat=records.jcat AND b.norad_id IS NOT NULL)''')
        self.con.execute('''UPDATE properties SET norad_id=(SELECT r.norad_id FROM records r
          WHERE r.provider=properties.provider AND r.source_key=properties.source_key)
          WHERE provider='gcat' ''')
        self.con.commit()

    def sync_gcat(self, *, catalogs=GCAT_DEFAULT, refresh=False, fetch=_raw_request):
        for name in catalogs:
            if name not in GCAT_FULL:
                raise ValueError('Unknown GCAT catalog: '+name)
            job = 'tsv:'+name
            if not refresh and self._get_state('gcat',job) and self._get_state('gcat',job)['complete']:
                print('[GCAT] cached:',name,flush=True)
                continue
            url=GCAT_BASE+name+'.tsv'
            _, _, raw = fetch(url,{'User-Agent':'Orbitoby-Physical-Archive/1.0'})
            n=self.import_gcat_tsv(name+'.tsv',raw,url)
            self._update_state('gcat',job,'done',complete=True,increment=1)
            print(f'[GCAT] {name}: {n:,} rows',flush=True)

    def import_discos_page(self, data, *, group, url, raw=None):
        if not isinstance(data,dict) or not isinstance(data.get('data'),list):
            raise ArchiveError('Unexpected ESA DISCOS response envelope')
        count=0
        for obj in data['data']:
            if not isinstance(obj,dict) or not isinstance(obj.get('attributes'),dict):
                raise ArchiveError('Unexpected ESA DISCOS object shape')
            a=obj['attributes']
            norad=_norad(_key_get(a,'satno'))
            source_key=str(obj.get('id') or 'satno:'+str(norad))
            field_specs=(
                ('catalog_mass_kg','mass','kg','Catalog mass, not necessarily current in-orbit mass'),
                ('cross_section_geo_avg_m2','xSectAvg','m2','Geometric area; not aerodynamic drag area'),
                ('cross_section_geo_min_m2','xSectMin','m2','Geometric minimum'),
                ('cross_section_geo_max_m2','xSectMax','m2','Geometric maximum'),
                ('shape','shape',None,'Geometry label'),
                ('body_width_m','width','m','Body dimension'),
                ('body_height_m','height','m','Body dimension'),
                ('body_depth_m','depth','m','Body dimension'),
                ('body_diameter_m','diameter','m','Body dimension'),
                ('body_span_m','span','m','Body or deployed span (source-defined)'),
                ('object_class','objectClass',None,'Catalog object class'),
            )
            fields=[(d,_key_get(a,k),u,k,n) for d,k,u,n in field_specs if _key_get(a,k) is not None]
            self._record('discos',source_key,norad,None,group,obj,url,fields)
            count+=1
        raw = raw if raw is not None else json.dumps(data,ensure_ascii=False).encode()
        self._receipt('discos',group,url,raw,count,'Accessible DISCOS objects page / filter')
        self.con.commit()
        return count

    def sync_discos_pages(self, *, max_pages=10, page_size=100, refresh=False, fetch=_raw_request):
        """Official paginated API v2; checkpoint after each page; never bypass account quotas.

        Run again to continue. A complete flag means the server returned a last page;
        it does not certify that private/restricted objects were provided.
        """
        if not (1 <= page_size <= 100):
            raise ValueError('page_size must be 1..100')
        if max_pages < 1:
            raise ValueError('max_pages must be positive')
        token=os.environ.get('ORBITOBY_DISCOS_TOKEN')
        if not token:
            raise ArchiveError('ORBITOBY_DISCOS_TOKEN is missing')
        job='all_pages'
        st=self._get_state('discos',job)
        if st and st['complete'] and not refresh:
            print('[DISCOS] all accessible pages already traversed; --refresh to restart',flush=True)
            return
        page=1 if refresh or not st or not st['cursor'] else int(st['cursor'])
        for _ in range(max_pages):
            url=DISCOS_BASE+'?'+urlencode({'page[size]':page_size,'page[number]':page})
            headers={'Authorization':'Bearer '+token,'DiscosWeb-Api-Version':'2','User-Agent':'Orbitoby-Physical-Archive/1.0'}
            try:
                _,response_headers,raw=fetch(url,headers)
                data=json.loads(raw)
                n=self.import_discos_page(data,group=f'page_{page:06d}',url=url,raw=raw)
            except (ArchiveError, OSError, ValueError) as exc:
                self._update_state('discos',job,str(page),error=str(exc))
                raise
            # Page semantics are standard JSON:API. A short or empty page ends scan.
            # If links.next explicitly absent/NULL, it also signals completion.
            links=data.get('links')
            no_next=isinstance(links,dict) and 'next' in links and not links['next']
            done=n < page_size or no_next
            self._update_state('discos',job,str(page+1),complete=done,increment=1)
            print(f'[DISCOS] page={page}; records={n}; completed={done}',flush=True)
            if done:
                break
            remaining = next((v for k,v in response_headers.items()
                              if k.casefold() in ('x-ratelimit-remaining','x-rate-limit-remaining')), None)
            if remaining is not None and str(remaining).strip() == '0':
                print('[DISCOS] Server reports zero remaining requests; resume after reset',flush=True)
                break
            page+=1

    def import_keeptrack_bulk(self, data, *, url=KEEPTRACK_BULK, raw=None, source_group='brief'):
        objects=_records_from_bulk(data)
        if not objects or not all(isinstance(r,dict) for r in objects):
            raise ArchiveError('Empty or malformed KeepTrack bulk response')
        self.con.execute("DELETE FROM properties WHERE provider='keeptrack' AND source_key IN "
                         "(SELECT source_key FROM records WHERE provider='keeptrack' AND source_group=?)", (source_group,))
        self.con.execute("DELETE FROM records WHERE provider='keeptrack' AND source_group=?", (source_group,))
        have_ids=0
        count=0
        for i,obj in enumerate(objects):
            # No guessing of generic 'id' (which can be a KeepTrack-internal ID).
            n=_keeptrack_norad(obj)
            if n is not None:
                have_ids+=1
            # Preserve every raw field even for non-mappable records.
            source_key=source_group+':'+(str(n) if n is not None else 'unmatched:'+str(i))
            # Duplicate IDs in a payload are disallowed, not silently picked.
            if self.con.execute('SELECT 1 FROM records WHERE provider=? AND source_key=?',('keeptrack',source_key)).fetchone():
                # On refresh same source key is expected: replaced below.
                pass
            fields=[]
            # Bulk brief often supplies an RCS category, NOT drag cross-sectional area.
            for dest,source,unit,note in (
                ('rcs_category','RCS',None,'Radar cross section class; never aerodynamic drag area'),
                ('object_class','OBJECT_TYPE',None,'Catalog class'),
                ('satellite_name','OBJECT_NAME',None,'Object name'),
                ('launch_date','LAUNCH_DATE',None,'Date'),
                ('purpose','PURPOSE',None,'Mission purpose'),
            ):
                v=_key_get(obj,source,{'OBJECT_TYPE':'type','OBJECT_NAME':'name','LAUNCH_DATE':'launchDate','PURPOSE':'purpose','RCS':'rcs'}.get(source,source))
                if v is not None:
                    fields.append((dest,v,unit,source,note))
            # The bulk brief format does not promise detailed mass and area.
            # Explicit unit-bearing fields in a provider-approved detailed export
            # can be normalized without treating arbitrary Mass or RCS as kg/m2.
            for dest, aliases, unit, note in (
                ('reported_mass_kg',('mass_kg','massKg'),'kg','Source-reported mass; epoch unknown'),
                ('reported_dry_mass_kg',('dry_mass_kg','dryMassKg'),'kg','Source-reported dry mass'),
                ('reported_length_m',('length_m','lengthM'),'m','Dimension'),
                ('reported_diameter_m',('diameter_m','diameterM'),'m','Dimension'),
                ('reported_span_m',('span_m','spanM'),'m','Dimension'),
                ('reported_power_w',('power_w','powerW'),'W','Power'),
            ):
                val=_key_get(obj,*aliases)
                if val is not None:
                    fields.append((dest,val,unit,aliases[0],note))
            self._record('keeptrack',source_key,n,None,source_group,obj,url,fields)
            count+=1
        if have_ids == 0:
            self.con.rollback()
            raise ArchiveError('KeepTrack bulk records have no recognized NORAD IDs; check source schema')
        raw = raw if raw is not None else json.dumps(data,ensure_ascii=False).encode()
        self._receipt('keeptrack',source_group,url,raw,count,'Active catalog bulk; not historical full detailed metadata')
        self.con.commit()
        return count, have_ids

    def sync_keeptrack(self, *, refresh=False, fetch=_raw_request):
        """One official bulk call only, never per-satellite harvesting."""
        token=os.environ.get('ORBITOBY_KEEPTRACK_API_KEY')
        if not token:
            raise ArchiveError('ORBITOBY_KEEPTRACK_API_KEY is missing')
        st=self._get_state('keeptrack','brief')
        if st and st['complete'] and not refresh:
            print('[KeepTrack] cached. Use --refresh to update.',flush=True)
            return
        headers={'X-API-Key':token,'User-Agent':'Orbitoby-Physical-Archive/1.0'}
        # ETag-aware update if possible; keep local DB if server returns 304.
        tag_path=self.path/'keeptrack_brief_etag.txt'
        if refresh and tag_path.exists():
            headers['If-None-Match']=tag_path.read_text().strip()
        status,response_headers,raw=fetch(KEEPTRACK_BULK,headers)
        if status == 304:
            print('[KeepTrack] unchanged (304)',flush=True)
            return
        n,mapped=self.import_keeptrack_bulk(json.loads(raw),raw=raw)
        etag = next((v for k,v in response_headers.items() if k.casefold()=='etag'),None)
        if etag:
            tag_path.write_text(str(etag))
        self._update_state('keeptrack','brief','done',complete=True,increment=1)
        print(f'[KeepTrack] official bulk brief: {n:,} objects; mapped IDs={mapped:,}',flush=True)

    def import_authorized_keeptrack_file(self,path):
        """Import *provider-approved* detailed bulk export, not per-ID scraping."""
        p=Path(path).expanduser()
        raw=p.read_bytes()
        if p.suffix.lower()=='.gz':
            raw=gzip.decompress(raw)
        data=json.loads(raw)
        result=self.import_keeptrack_bulk(data,raw=raw,url='authorized-export:'+p.name,source_group='authorized_detail')
        self._update_state('keeptrack','authorized_detail','done',complete=True,increment=1)
        return result

    def sources(self):
        rows=self.con.execute('''SELECT provider, COUNT(*) AS records,
                COUNT(DISTINCT norad_id) AS norad_ids FROM records GROUP BY provider''').fetchall()
        return {r['provider']:{'records':r['records'],'norad_ids':r['norad_ids']} for r in rows}

    def state(self):
        return [dict(r) for r in self.con.execute('SELECT * FROM state ORDER BY provider,job')]

    def get(self,norad_id, *, provider=None, include_raw=True):
        n=_norad(norad_id)
        if n is None: raise ValueError('Valid NORAD ID required')
        sql='SELECT * FROM records WHERE norad_id=?'
        params=[n]
        if provider:
            sql+=' AND provider=?';params.append(provider)
        records=[dict(row) for row in self.con.execute(sql+' ORDER BY provider,source_group',params)]
        for r in records:
            r['raw'] = json.loads(r.pop('raw_json')) if include_raw else None
        sql2='SELECT provider,source_key,field,value_numeric,value_text,unit,source_field,caveat FROM properties WHERE norad_id=?'
        par=[n]
        if provider:
            sql2+=' AND provider=?';par.append(provider)
        properties=[dict(row) for row in self.con.execute(sql2+' ORDER BY provider,field',par)]
        return {'norad_id':n,'records':records,'properties':properties}

    def raw(self,norad_id,provider):
        return [r['raw'] for r in self.get(norad_id,provider=provider)['records']]

    def select(self, *, required=(), provider=None):
        """IDs possessing every requested explicit normalized property; no guessed properties."""
        conditions=[]; args=[]
        for field in required:
            conditions.append('''EXISTS (SELECT 1 FROM properties p WHERE p.norad_id=r.norad_id
               AND p.field=? AND (p.value_numeric>0 OR p.value_text IS NOT NULL) ''' +
               (' AND p.provider=?' if provider else '') + ')')
            args.append(field)
            if provider: args.append(provider)
        q='SELECT DISTINCT r.norad_id FROM records r WHERE r.norad_id IS NOT NULL'
        if provider:
            q+=' AND r.provider=?';args=[provider]+args
        if conditions:q+=' AND '+' AND '.join(conditions)
        q+=' ORDER BY r.norad_id'
        return [row[0] for row in self.con.execute(q,args)]

    def coverage(self):
        return [dict(row) for row in self.con.execute('''SELECT provider,field,
          COUNT(DISTINCT norad_id) AS objects_with_field FROM properties
          WHERE norad_id IS NOT NULL AND (value_numeric>0 OR value_text IS NOT NULL)
          GROUP BY provider,field ORDER BY provider,field''')]

    def collisions(self,field, *, relative_tolerance=0.05):
        """Only compare explicitly same normalized field between sources."""
        if not (0<=relative_tolerance<=1): raise ValueError('tolerance between 0 and 1')
        rows=self.con.execute('''SELECT norad_id, provider, value_numeric FROM properties
            WHERE field=? AND norad_id IS NOT NULL AND value_numeric>0
            ORDER BY norad_id,provider''',(field,)).fetchall()
        grouped={}
        for r in rows: grouped.setdefault(r['norad_id'], []).append((r['provider'],r['value_numeric']))
        out=[]
        for n, vals in grouped.items():
            if len({s for s,_ in vals})<2: continue
            numbers=[v for _,v in vals]
            spread=(max(numbers)-min(numbers))/max(numbers)
            if spread>relative_tolerance:
                out.append({'norad_id':n,'field':field,'relative_spread':spread,'sources':vals})
        return out

    def audit_universe(self, norad_ids):
        """Audit a full reference catalog without orbit/epoch/altitude filters."""
        ids={_norad(x) for x in norad_ids}
        if None in ids: raise ValueError('Universe contains a missing/invalid NORAD ID')
        if not ids: raise ValueError('Reference NORAD universe cannot be empty')
        result={'reference_norad_count':len(ids),'providers':{}}
        for provider in ('gcat','discos','keeptrack'):
            matched={r[0] for r in self.con.execute(
                'SELECT DISTINCT norad_id FROM records WHERE provider=? AND norad_id IS NOT NULL',(provider,))}
            result['providers'][provider]={
                'matched':len(ids & matched),
                'unmatched':len(ids - matched),
                'provider_ids_outside_reference':len(matched-ids),
                'coverage_fraction':round(len(ids & matched)/len(ids),6),
                'missing_norad_ids':sorted(ids-matched),
            }
        return result

    def find_raw(self,provider,field, *, expected=None, limit=None):
        """Find provider-native fields WITHOUT discarding unnormalized metadata.

        `field` may be a dotted JSON path, e.g. `attributes.mass` for DISCOS.
        Unlike normalized fields, no unit/meaning is inferred; caller inspects
        the provider documentation before interpreting numeric values.
        """
        if provider not in ('gcat','discos','keeptrack'):
            raise ValueError('provider must be gcat/discos/keeptrack')
        if not field or not all(x and not x.startswith('_') for x in field.split('.')):
            raise ValueError('Valid dotted field path required')
        results=[]
        for row in self.con.execute('SELECT norad_id,source_key,raw_json FROM records WHERE provider=?',(provider,)):
            obj=json.loads(row['raw_json'])
            val=obj
            for part in field.split('.'):
                if not isinstance(val,dict):
                    val=None;break
                val=_key_get(val,part)
            if val is not None and (expected is None or val==expected):
                results.append({'norad_id':row['norad_id'],'source_key':row['source_key'],'value':val})
                if limit is not None and len(results)>=limit:
                    break
        return results

    def export_wide(self, path, *, universe=None, required=()):
        """Provider-prefixed wide CSV; preserve missing reference IDs and conflicts."""
        selection=set(self.select(required=required)) if required else None
        if universe is not None:
            ids={_norad(x) for x in universe}
            if None in ids: raise ValueError('Universe has invalid NORAD identifiers')
        else:
            ids={r[0] for r in self.con.execute('SELECT DISTINCT norad_id FROM records WHERE norad_id IS NOT NULL')}
        if selection is not None: ids &= selection
        values={x:{} for x in ids}
        colnames=set()
        for r in self.con.execute('SELECT norad_id, provider, field, value_text FROM properties WHERE norad_id IS NOT NULL ORDER BY norad_id,provider,field'):
            n=r['norad_id']
            if n not in values:continue
            col=r['provider']+'.'+r['field']
            colnames.add(col)
            values[n].setdefault(col,set()).add(str(r['value_text']))
        p=Path(path).expanduser();p.parent.mkdir(parents=True,exist_ok=True)
        columns=sorted(colnames)
        with p.open('w',newline='',encoding='utf-8') as f:
            w=csv.writer(f);w.writerow(['norad_id']+columns)
            for n in sorted(ids):
                w.writerow([n]+[' | '.join(sorted(values[n].get(c,()))) for c in columns])
        return p

    def export_csv(self, path, *, required=()):
        """Long-form evidence CSV; never silently average or resolve conflicts."""
        ids=set(self.select(required=required)) if required else None
        p=Path(path).expanduser();p.parent.mkdir(parents=True,exist_ok=True)
        with p.open('w',newline='',encoding='utf-8') as f:
            w=csv.writer(f);w.writerow(('norad_id','provider','source_key','field','value_numeric','value_text','unit','source_field','caveat'))
            for row in self.con.execute('''SELECT norad_id,provider,source_key,field,value_numeric,value_text,unit,source_field,caveat
                                          FROM properties ORDER BY norad_id,provider,field'''):
                if ids is None or row['norad_id'] in ids:
                    w.writerow(list(row))
        return p



    def satellites(self, *, catalog=None, required=(),
                   satellites_only=True, include_sources=False,
                   tle_parquet=None, conflict_tolerance=0.05):
        """Unified physical metadata with optional TLE history."""
        from .physical_research import query_physical
        return query_physical(
            self,
            catalog=catalog,
            required=required,
            satellites_only=satellites_only,
            include_sources=include_sources,
            tle_parquet=tle_parquet,
            conflict_tolerance=conflict_tolerance,
        )


def physics(path=None):
    """Orbitoby grammar: `from orbitoby import physics; db=physics(path)`.

    The lightweight module also works via `from orbitoby.physical_archives import physics`.
    """
    return PhysicalArchive.open(path)
