Checked-in systemd unit templates for the five node units plus the separate
qmx-observability.service (not a node unit).

Node units (AR-78 / DEC-0201):
  qmn.service
  qmn-news-calendar.{service,timer}
  qmn-backup.{service,timer}
  qmn-restore-sample.{service,timer}
  qmn-restore-full.{service,timer}

Separate sixth unit (DEC-0200):
  qmx-observability.service

Templates live under templates/. Files ending in .in carry @DRAIN_WINDOW_SEC@
and @WATCHDOG_INTERVAL_SEC@ placeholders rendered by just node-install from the
resolved config artifact — never hand-authored (DEC-0189 / DEC-0201).

Hardening contract (DEC-0227 / NFR-14):
  User=qmx (fixed; never DynamicUser) on all five node units
  ProtectSystem=strict + ReadWritePaths=/var/lib/qmx
  NoNewPrivileges, PrivateTmp, ProtectHome
  RestrictAddressFamilies=AF_UNIX AF_INET AF_INET6
  LoadCredentialEncrypted per unit for that unit's credentials only
  Credentials sealed with systemd-creds encrypt --with-key=host (never auto)

qmx-observability.service runs as User=qmxobs with ReadWritePaths under
/var/lib/qmx-observability and holds zero node authority.
