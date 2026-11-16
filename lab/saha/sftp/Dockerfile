# Karsi taraf SFTP sunucusu: parola ve anahtar ile giris, sirket disi bir sistemi temsil eder.
FROM alpine:3.20
RUN apk add --no-cache openssh-server openssh-sftp-server coreutils shadow tzdata && ssh-keygen -A
COPY sshd_config /etc/ssh/sshd_config
COPY entry.sh /entry.sh
CMD ["sh", "/entry.sh"]
