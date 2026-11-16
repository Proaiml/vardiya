#!/bin/sh
# Hesaplar ilk aciliste kurulur; senaryolar parolalari ve anahtarlari sonradan degistirebilir.
mk() { id "$1" >/dev/null 2>&1 || { adduser -D -s /bin/sh "$1"; echo "$1:$2" | chpasswd; }
  mkdir -p "/home/$1/in" "/home/$1/out" "/home/$1/arsiv" "/home/$1/.ssh"
  touch "/home/$1/.ssh/authorized_keys"; chmod 700 "/home/$1/.ssh"; chmod 600 "/home/$1/.ssh/authorized_keys"
  chown -R "$1:$1" "/home/$1"; }
mk mftuser 'Mft-2026-Ilk'
mk banka 'Banka-2026-Ilk'
mk rapor 'Rapor-2026-Ilk'
exec /usr/sbin/sshd -D -e
