FROM ubuntu:20.04

RUN apt-get update \
    && DEBIAN_FRONTEND=noninteractive apt-get install -y samba \
    && rm -rf /var/lib/apt/lists/*

RUN groupadd -r samba \
    && useradd -r -g samba k8s \
    && (echo "password"; echo "password") | smbpasswd -a -s k8s \
    && smbpasswd -e k8s \
    && mkdir -p /data/sambashare

COPY smb.conf /etc/samba/smb.conf
COPY startup.sh /root/startup.sh
RUN chmod +x /root/startup.sh

CMD ["/root/startup.sh"]
