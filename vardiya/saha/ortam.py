"""The standard site of the live lab and its reset.

Every episode starts from the same site: accounts, directories, keys, tables, connection profiles and a handful
of scripts. `sifirla` puts every host back, whatever the previous episode (or the agent under test) did to it.
"""
import time

from .lab import AGENTS

SFTP_USERS = {"mftuser": "Mft-2026-Ilk", "banka": "Banka-2026-Ilk", "rapor": "Rapor-2026-Ilk"}
DB_USERS = {"etl_user": "Etl-2026-Ilk", "rapor_user": "Rapor-2026-Ilk"}

PROFILES = {
    "SFTP_KARSI": {"Type": "ConnectionProfile:FileTransfer:SFTP", "HostName": "dosya-sunucu", "Port": "22",
                   "User": "mftuser", "Password": SFTP_USERS["mftuser"]},
    "SFTP_BANKA": {"Type": "ConnectionProfile:FileTransfer:SFTP", "HostName": "dosya-sunucu", "Port": "22",
                   "User": "banka", "PrivateKeyName": "banka_key"},
    "YEREL_BATCH": {"Type": "ConnectionProfile:FileTransfer:Local", "User": "batch"},
    "YEREL_ETL": {"Type": "ConnectionProfile:FileTransfer:Local", "User": "etl"},
    "PG_UYG": {"Type": "ConnectionProfile:Database:PostgreSQL", "Host": "appdb", "Port": "5432", "User": "etl_user",
               "Password": DB_USERS["etl_user"], "DatabaseName": "uygulama"},
    "PG_RAPOR": {"Type": "ConnectionProfile:Database:PostgreSQL", "Host": "appdb", "Port": "5432", "User": "rapor_user",
                 "Password": DB_USERS["rapor_user"], "DatabaseName": "uygulama"},
}

# Agent hosts whose PID 1 is the supervisor (lab/saha/agent/bin/ajan-denetci): the agent service may have been
# stopped or its settings broken by the previous episode; put the settings back and start it.
AGENT_SERVICE_RESET = r"""
if grep -q ajan-denetci /proc/1/cmdline 2>/dev/null; then
  mkdir -p /etc/ctm && printf 'JAVA_OPTIONS="-Xmx256m"\nHTTP_PORT=4445\n' > /etc/ctm/ajan.conf
  /opt/ctm/bin/ctmag status >/dev/null || /opt/ctm/bin/ctmag start
fi
"""

KILL_MARKED = r"""for p in /proc/[0-9]*; do grep -qz '^SAHA_ARIZA=1' $p/environ 2>/dev/null && kill -9 ${p#/proc/} 2>/dev/null; done; true"""
AGENT_SERVICE_RESTART = r"""grep -q ajan-denetci /proc/1/cmdline 2>/dev/null && /opt/ctm/bin/ctmag restart sifirlama; true"""

AGENT_RESET = r"""
for p in /proc/[0-9]*; do grep -qz '^SAHA_ARIZA=1' $p/environ 2>/dev/null && kill -9 ${p#/proc/} 2>/dev/null; done
for u in batch etl finans mft; do pkill -u $u 2>/dev/null; passwd -u $u >/dev/null 2>&1; done
rm -rf /data/gelen /data/giden /data/arsiv /data/tmp /data/dar/* /data/dar/.[!.]* /app/scripts /app/sql /var/log/app /opt/ctm/keys/* /opt/ctm/run/* /tmp/saha-*
mkdir -p /data/gelen /data/giden /data/arsiv /data/tmp /app/scripts /app/sql /var/log/app
chown -R batch:batch /data/gelen /data/giden /data/arsiv /app /var/log/app
chmod 0775 /data/gelen /data/giden /data/arsiv; chmod 0777 /data/tmp /opt/ctm/run; chmod 1777 /data/dar
chown jobscheduler /opt/ctm/cp /opt/ctm/keys; chmod 0755 /opt/ctm/cp; chmod 0700 /opt/ctm/keys
addgroup etl batch 2>/dev/null; addgroup finans batch 2>/dev/null; addgroup mft batch 2>/dev/null
cat > /app/scripts/gunluk_satis.sh <<'EOS'
#!/bin/sh
# Gunun satis dosyasini uretir: /data/giden/satis_<YYYYMMDD>.csv
gun=${1:-$(date +%Y%m%d)}
out=/data/giden/satis_${gun}.csv
{ echo "id,tarih,tutar"; i=1; while [ $i -le 20 ]; do echo "$i,$gun,$((i * 15))"; i=$((i + 1)); done; } > "$out"
echo "uretildi: $out $(wc -l < "$out") satir"
EOS
cat > /app/scripts/arsivle.sh <<'EOS'
#!/bin/sh
# Gonderilmis dosyalari arsive tasir.
set -e
n=0
for f in /data/giden/*.csv; do [ -f "$f" ] || continue; mv "$f" /data/arsiv/; n=$((n + 1)); done
echo "arsivlenen dosya: $n"
EOS
cat > /app/sql/satis_yukle.sql <<'EOS'
-- Gelen satis dosyasini satis tablosuna yukler. Parametre: gun (YYYYMMDD)
\set dosya '/data/gelen/satis_' :gun '.csv'
\set yukle '\\copy satis_gecici from ' :'dosya' ' with (format csv, header true)'
:yukle
insert into satis (id, tarih, tutar) select id, tarih, tutar from satis_gecici;
insert into yukleme_log (dosya, satir) select 'satis_' || :'gun' || '.csv', count(*) from satis_gecici;
truncate satis_gecici;
EOS
chown -R batch:batch /app; chmod 0755 /app/scripts/*.sh; chmod 0644 /app/sql/*.sql
"""

SFTP_RESET = r"""
for p in /proc/[0-9]*; do grep -qz '^SAHA_ARIZA=1' $p/environ 2>/dev/null && kill -9 ${p#/proc/} 2>/dev/null; done
rm -rf /srv/dar/* /srv/dar/.[!.]* 2>/dev/null
for u in mftuser banka rapor; do
  id $u >/dev/null 2>&1 || adduser -D -s /bin/sh $u
  passwd -u $u >/dev/null 2>&1
  rm -rf /home/$u; mkdir -p /home/$u/in /home/$u/out /home/$u/arsiv /home/$u/.ssh
  : > /home/$u/.ssh/authorized_keys; chmod 700 /home/$u/.ssh; chmod 600 /home/$u/.ssh/authorized_keys
  chown -R $u:$u /home/$u; chmod 755 /home/$u
done
"""

DB_RESET = """
select pg_terminate_backend(pid) from pg_stat_activity where datname = 'uygulama' and pid <> pg_backend_pid();
drop schema if exists public cascade;
create schema public;
do $$ begin
  if not exists (select from pg_roles where rolname = 'etl_user') then create role etl_user login; end if;
  if not exists (select from pg_roles where rolname = 'rapor_user') then create role rapor_user login; end if;
end $$;
alter role etl_user with login password '%(etl)s' connection limit -1 valid until 'infinity';
alter role rapor_user with login password '%(rapor)s' connection limit -1 valid until 'infinity';
grant usage, create on schema public to etl_user;
grant usage on schema public to rapor_user;
create table satis (id int primary key, tarih text not null, tutar numeric not null);
create table satis_gecici (id int, tarih text, tutar numeric);
create table yukleme_log (dosya text, satir int, zaman timestamptz default now());
create table musteri (id int primary key, ad text not null, sehir text);
insert into musteri select g, 'Musteri ' || g, (array['Ankara','Izmir','Bursa'])[1 + g %% 3] from generate_series(1, 50) g;
alter table satis owner to etl_user; alter table satis_gecici owner to etl_user; alter table yukleme_log owner to etl_user;
grant select on all tables in schema public to rapor_user;
grant select, insert, update, delete on musteri to etl_user;
"""


def sifirla(lab, ctm, bekle=120):
    """Bring every host and the scheduler back to the standard site. Returns the seconds it took."""
    t0 = time.time()
    for host in ("ajan1", "ajan2", "dosya-sunucu", "appdb"):
        rc, out = lab.docker("inspect", "-f", "{{.State.Running}} {{.State.Paused}}", lab.container(host))
        state = out.split()[:2]
        if state == ["true", "true"]:
            lab.power(host, "unpause")
        elif state != ["true", "false"]:
            lab.power(host, "start")
    for host in AGENTS:
        # a stray process from the previous scene (it may hold the agent's port) goes first, then the service
        lab.sh(host, KILL_MARKED, timeout=30)
        lab.sh(host, AGENT_SERVICE_RESET, timeout=60)
    for _ in range(40):
        if lab.sh("appdb", "pg_isready -U postgres -d uygulama")[0] == 0:
            break
        time.sleep(1)
    try:
        lab.wait_ready(min(bekle, 60))
    except RuntimeError:
        # an agent that runs but does not couple (wrong port, stale state): restart its service once
        for host, state in (lab.agent_states() or {}).items():
            if state != "COUPLED":
                lab.sh(host, AGENT_SERVICE_RESTART, timeout=90)
        lab.wait_ready(bekle)
    ctm.reset()
    for host in AGENTS:
        rc, out = lab.sh(host, AGENT_RESET)
    lab.sh("dosya-sunucu", SFTP_RESET)
    for user, pw in SFTP_USERS.items():
        lab.sh("dosya-sunucu", "chpasswd", stdin=f"{user}:{pw}\n")
    # the bank account logs in with a key only; the key pair lives on the agents
    lab.sh("ajan1", "rm -f /opt/ctm/keys/banka_key*; ssh-keygen -q -t ed25519 -N '' -C saha-banka -f /opt/ctm/keys/banka_key "
                    "&& chmod 600 /opt/ctm/keys/banka_key", user="jobscheduler")
    _, priv = lab.sh("ajan1", "cat /opt/ctm/keys/banka_key")
    _, pub = lab.sh("ajan1", "cat /opt/ctm/keys/banka_key.pub")
    lab.sh("ajan2", "cat > /opt/ctm/keys/banka_key && chmod 600 /opt/ctm/keys/banka_key", user="jobscheduler", stdin=priv)
    lab.sh("ajan2", "cat > /opt/ctm/keys/banka_key.pub", user="jobscheduler", stdin=pub)
    lab.sh("dosya-sunucu", "cat > /home/banka/.ssh/authorized_keys && chown banka:banka /home/banka/.ssh/authorized_keys "
                           "&& chmod 600 /home/banka/.ssh/authorized_keys", stdin=pub)
    lab.sql(DB_RESET % {"etl": DB_USERS["etl_user"], "rapor": DB_USERS["rapor_user"]})
    ctm.deploy(PROFILES)
    return round(time.time() - t0, 1)
