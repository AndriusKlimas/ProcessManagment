#!/bin/bash
set -e

mkdir -p /data/sambashare
chown -R k8s:samba /data/sambashare
chmod -R ug+rwX /data/sambashare

exec smbd --foreground --no-process-group
