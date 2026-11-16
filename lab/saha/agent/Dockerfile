# JS7 ajan imaji + islerin gercekten kullandigi istemciler (sftp, psql) ve is calistiran hesaplar.
# Ajan sureci `jobscheduler` hesabiyla calisir; isler "RunAs" hesabina sudo ile gecer (yalnizca izinli hesaplara).
FROM sosberlin/js7:agent-2-9-1
USER root
RUN apk add --no-cache openssh-client sshpass postgresql-client coreutils procps util-linux tzdata findutils grep sed gawk sudo python3 jq \
 && n=2001; for u in batch etl finans mft; do adduser -D -u $n -s /bin/sh "$u"; n=$((n+1)); done \
 && mkdir -p /data/gelen /data/giden /data/arsiv /data/tmp /app/scripts /app/sql /opt/ctm/cp /opt/ctm/keys /opt/ctm/run /var/log/app \
 && chown -R batch:batch /data /app /var/log/app && chmod 0777 /data/tmp /opt/ctm/run \
 && chown 1001 /opt/ctm/cp /opt/ctm/keys /opt/ctm/run && chmod 0755 /opt/ctm/cp && chmod 0700 /opt/ctm/keys \
 && echo "jobscheduler ALL=(batch,etl,finans,mft) NOPASSWD:SETENV: ALL" > /etc/sudoers.d/ctm && chmod 0440 /etc/sudoers.d/ctm
