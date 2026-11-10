"""Read the published GPS catalogue in a disposable, offline PostGIS instance."""

import json
import subprocess
import sys
import uuid


# Same PostgreSQL/PostGIS image as the GPS catalogue's v2 release builder.
POSTGIS_IMAGE = 'postgis/postgis:18-3.6@sha256:4a43e3c3e5d55b9208240fc71db543b79c638766280c625a425bd0a2390989c4'

# Keep the source geometry as its SRID and native coordinates. The source view
# also provides the coordinates in each of the two CRS used by the map.
PROJECTION = """
BEGIN READ ONLY;
WITH cave_details AS (
    SELECT to_jsonb(c) || jsonb_build_object('citations', ARRAY(
        SELECT to_jsonb(r) || jsonb_build_object('publication', to_jsonb(p))
        FROM catalog.cave_citations r JOIN catalog.publications p ON p.id = r.publication_id
        WHERE r.cave_id = c.id ORDER BY r.ordinal
    )) AS detail, c.id
    FROM catalog.caves c
), object_details AS (
    SELECT to_jsonb(o) || jsonb_build_object('citations', ARRAY(
        SELECT to_jsonb(r) || jsonb_build_object('publication', to_jsonb(p))
        FROM catalog.object_citations r JOIN catalog.publications p ON p.id = r.publication_id
        WHERE r.object_id = o.id ORDER BY r.ordinal
    )) AS detail, o.id
    FROM catalog.objects o
), measurement_details AS (
    SELECT (to_jsonb(m) - ARRAY['input_geom', 'geom_wgs84', 'geom_1992']) ||
        jsonb_build_object(
            'tags', ARRAY(SELECT t.tag FROM catalog.measurement_tags t
                WHERE (t.object_id, t.measurement_id) = (m.object_id, m.id) ORDER BY t.ordinal),
            'citations', ARRAY(
                SELECT to_jsonb(r) || jsonb_build_object('publication', to_jsonb(p))
                FROM catalog.measurement_citations r JOIN catalog.publications p ON p.id = r.publication_id
                WHERE (r.object_id, r.measurement_id) = (m.object_id, m.id) ORDER BY r.ordinal
            )
        ) AS detail, m.object_id, m.history_order
    FROM catalog.v_measurements m
), flags AS (
    SELECT 'error' AS severity, code, entity_id, NULL AS measurement_id, NULL AS detail
    FROM catalog.v_integrity_issues
    UNION ALL SELECT 'warning', code, entity_id, measurement_id, NULL FROM catalog.v_warnings
    UNION ALL SELECT 'warning', code, entity_id, NULL, NULL FROM catalog.v_domain_warnings
    UNION ALL SELECT severity, code, entity_id, measurement_id, detail FROM catalog.v_geography_issues
)
SELECT json_build_object(
    'objects', ARRAY(SELECT detail FROM object_details ORDER BY id),
    'caves', ARRAY(SELECT detail FROM cave_details ORDER BY id),
    'measurements', ARRAY(SELECT detail FROM measurement_details ORDER BY object_id, history_order),
    'best_measurements', ARRAY(SELECT json_build_object(
        'object_id', b.object_id, 'measurement_id', b.id, 'mode', b.best_mode,
        'reason', b.best_reason, 'rejected_fallback', b.rejected_fallback,
        'manual_measurement_id', p.manual_measurement_id,
        'computed_best_measurement_id', a.measurement_id,
        'updated_at', p.updated_at, 'updated_by', p.updated_by
    ) FROM catalog.v_best b
      JOIN catalog.best_policy p USING (object_id)
      JOIN catalog.v_auto_best a USING (object_id) ORDER BY b.object_id),
    'object_external_refs', ARRAY(SELECT r FROM catalog.object_external_refs r ORDER BY object_id, ordinal),
    'cave_external_refs', ARRAY(SELECT r FROM catalog.cave_external_refs r ORDER BY cave_id, ordinal),
    'relations', ARRAY(SELECT r FROM catalog.relations r ORDER BY id),
    'attachments', ARRAY(SELECT a FROM catalog.attachments a ORDER BY object_id, ordinal),
    'metadata', json_build_object(
        'engine', 'PostgreSQL/PostGIS', 'postgresql', current_setting('server_version'),
        'postgis', public.postgis_full_version(), 'image', :'image'
    ),
    'validation_flags', ARRAY(SELECT f FROM flags f ORDER BY severity, code, entity_id, measurement_id, detail)
);
COMMIT;
"""


def docker(args, *, timeout, data=None):
    try:
        return subprocess.run(['docker', *args], input=data, capture_output=True, check=True, timeout=timeout).stdout
    except FileNotFoundError as error:
        raise ValueError('Docker is required to import the GPS PostgreSQL dump') from error
    except subprocess.TimeoutExpired as error:
        raise ValueError(f'GPS PostGIS Docker command timed out: {args[0]}') from error
    except subprocess.CalledProcessError as error:
        raise ValueError(f'GPS PostGIS Docker command failed: {error.stderr.decode(errors="replace").strip()}') from error


def read_gps_dump(data):
    name = f'jktz-gps-{uuid.uuid4().hex}'
    try:
        docker(['run', '--detach', '--rm', '--name', name, '--network', 'none', '--platform', 'linux/amd64',
                '--tmpfs', '/var/lib/postgresql', '--env', 'POSTGRES_HOST_AUTH_METHOD=trust',
                '--env', 'POSTGRES_DB=catalogue', '--env', 'POSTGRES_INITDB_ARGS=--locale=C --encoding=UTF8',
                POSTGIS_IMAGE], timeout=300)
        # The image's bootstrap server listens only on its Unix socket.
        # TCP on the container's own loopback becomes ready after initialization.
        docker(['exec', name, 'sh', '-ec',
                'until pg_isready -h 127.0.0.1 -U postgres -d catalogue -q; do sleep 1; done'], timeout=120)
        docker(['exec', '-i', name, 'pg_restore', '--username=postgres', '--dbname=catalogue',
                '--single-transaction', '--no-owner', '--no-privileges'], data=data, timeout=180)
        projection = docker(['exec', '-i', name, 'psql', '--username=postgres', '--dbname=catalogue',
                             '--no-psqlrc', '--quiet', '--tuples-only', '--no-align', '--set=ON_ERROR_STOP=1',
                             '--set=image=' + POSTGIS_IMAGE], data=PROJECTION.encode(), timeout=180)
        return json.loads(projection)
    finally:
        # Also attempt cleanup after a timed-out run, which might have created the container.
        try:
            docker(['rm', '--force', name], timeout=30)
        except ValueError as error:
            if 'No such container' not in str(error):
                print(f'GPS PostGIS cleanup: {error}', file=sys.stderr)
