# LSTP-Cluster + OpenVZ Tutorial

# Table of Contents
1. [LTSP-Cluster](#LSTP-Cluster)
2. [Host Instalation](#host-instalation)
3. [Create ltsp-root01 (Terminal root)](#create-ltsp-root01-terminal-root)
4. [Create ltsp-control01 (Control center)](#create-ltsp-control01-control-center)
5. [Create ltsp-loadbalancer01 (Load Balancer)](#create-ltsp-loadbalancer01-load-Balancer)
6. [Create ltsp-appserv01 (First Application Server)](#create-ltsp-appserv01-first-application-server)
7. [Running](#Running)
8. [Troubleshoot](#Troubleshoot)
9. [References](#References)

# LSTP-Cluster
LTSP-Cluster is a set of LTSP plugins and client-side tools that allows you to deploy and centrally manage large numbers of thin-clients. It allows you to run thousands of thin-clients that are able to connect to a load-balanced cluster of GNU/Linux and-or Microsoft Windows terminal servers.

Some of the LTSP-Cluster Features are:
Central Configuration web interface
Load balanced thin clients across multiple servers
Complete autologin support with account creation
Store hardware information for all clients in the control center

In this tutorial, a basic setup of LTSP-Cluster will be installed. For this purpose, we will use VirtualBox where one x86_64/amd64 Ubuntu servers are configured as both the root server and application server.

Upfront to this tutorial, you must set a host network. Go to File > Host Network Manager > Create and set vboxnet0 like the image below:

![host network](https://github.com/flpmat/ltsp-cluster-openvz/blob/master/images/host-net-configuration.png)

Now, create one VirtualBox machine with one network interface connected to NAT and another network interface host-only.

![open vz network card](https://github.com/flpmat/ltsp-cluster-openvz/blob/master/images/ltsp-openvz-net.png)

Finnaly, create one VirtualBox machine for the thin client. Set it to boot throuhg the network. It should also have a network interface attached to the host-only network set previously. 

![thin client system](https://github.com/flpmat/ltsp-cluster-openvz/blob/master/images/thin-client-system.png)

# Host Installation

Install Ubuntu server (select the OpenSSH server role if you want SSH access). Once installed, reboot and make sure your system is up to date:
```
sudo apt-get update && sudo apt-get dist-upgrade
```
## Installing OpenVZ on Ubuntu 14.04

Switch to root user:
```
sudo su
```
First, we will add the OpenVZ Repository. Create a new entry on `/etc/apt/sources.list`:
```
deb http://download.openvz.org/debian wheezy main
deb http://download.openvz.org/debian wheezy-test main
```
Import OpenVZ GPG key:
```
wget --no-check-certificate --content-disposition https://github.com/flpmat/ltsp-cluster-openvz/blob/master/files/archive.key
apt-key add archive.key
```
Install OpenVZ kernel:
```
apt-get update
apt-get install linux-image-openvz-amd64
```
Exit sudo.

## Setting up Kernel parameters

Make sure you have added the following kernel parameters before logging into vz kernel:
```
vi /etc/sysctl.conf
```
Add the following lines:
```
# On Hardware Node we generally need
# packet forwarding enabled and proxy arp disabled
net.ipv4.ip_forward = 1
net.ipv6.conf.default.forwarding = 1
net.ipv6.conf.all.forwarding = 1
net.ipv4.conf.default.proxy_arp = 0

# Enables source route verification
net.ipv4.conf.all.rp_filter = 1

# Enables the magic-sysrq key
kernel.sysrq = 1

# We do not want all our interfaces to send redirects
net.ipv4.conf.default.send_redirects = 1
net.ipv4.conf.all.send_redirects = 0
```
## Remove all non-OpenVZ kernels
To list kernels:
```
rpm -qa kernel
```
Remove the kernel (example):
```
sudo apt remove --purge linux-image-4.4.0-21-generic
```
Reset GRUB:
```
sudo update-grub2
sudo reboot
```
Install vzctl, bridge-utils, bzr and plymouth-theme-ubuntu: 
```
sudo apt-get install vzctl bridge-utils bzr plymouth-theme-ubuntu-logo debootstrap
```
Reboot:
```
sudo reboot
```
## Creating the OpenVZ templates
Get the template generator script:
```
bzr get lp:~ubuntu-openvz-dev/openvz-tools/vz-utils
cd vz-utils/scripts/
```
Then run:
```
python vz-template-creator.py -v -a amd64 -D trusty -m http://archive.ubuntu.com/ubuntu ubuntu-14.04-amd64-server (if the host is amd64, use i386 otherwise)
python vz-template-creator.py -v -a i386 -D trusty -m http://archive.ubuntu.com/ubuntu ubuntu-16.04-i386-server (this one is i386 in all cases)
```
## Configure networking
Create `/etc/vz/vznet.conf`and add the following lines:
```
#!/bin/sh
EXTERNAL_SCRIPT="/usr/local/bin/vznetaddbr"
```
Create `/usr/local/bin/vznetaddbr` with the text below and make it executable:
```
#!/bin/bash
CTID=$VEID
CONFIGFILE=/etc/vz/conf/$CTID.conf
. $CONFIGFILE
VZHOSTIF=`echo $NETIF |sed 's/^.*host_ifname=\(.*\),.*$/\1/g'`
if [ ! -n "$VZHOSTIF" ]; then
   echo "According to $CONFIGFILE CT$CTID has no veth interface configured."
   exit 0
fi
if [ ! -n "$VZHOSTBR" ]; then
   echo "According to $CONFIGFILE CT$CTID has no bridge interface configured."
   exit 0
fi
echo "Adding interface $VZHOSTIF to bridge $VZHOSTBR on CT0 for CT$CTID"
/sbin/ifconfig $VZHOSTIF 0
echo 1 > /proc/sys/net/ipv4/conf/$VZHOSTIF/proxy_arp
echo 1 > /proc/sys/net/ipv4/conf/$VZHOSTIF/forwarding
/sbin/brctl addif $VZHOSTBR $VZHOSTIF
exit 0
```
To make `/usr/local/binvznetaddbr` executable:
```
sudo chmod +x /usr/local/binvznetaddbr
```
Add these two lines to `/etc/vz/conf/ve.basic.conf-sample`:
```config
CONFIG_CUSTOMIZED="yes"
VZHOSTBR="br0"
```
Add a bridge to `/etc/network/interfaces` (eth1 should be the second network card of your VBox machine, the one that is connected to the host-only network):
```
# The LAN interface
auto eth1
iface eth1 inet manual

# The first network bridge
auto br0
iface br0 inet static
 address 192.168.0.1
 netmask 255.255.255.0
 pre-up brctl addbr br0 && brctl addif br0 eth1
 post-down brctl delbr br0
```
Add these two lines to `/etc/rc.local`:
```
echo 1 > /proc/sys/net/ipv4/ip_forward
iptables -t nat -A POSTROUTING -o eth0 -j MASQUERADE
```
Reboot to make sure everything works.

# Create ltsp-root01 (Terminal root)
Create the VZ: 
```
sudo vzctl create 101 --ostemplate ubuntu-9.04-i386-server --hostname ltsp-root01 -config basic
```
Set the VZ name: 
```
sudo vzctl set 101 --name ltsp-root01 --save
```
Add a network card: 
```
sudo vzctl set ltsp-root01 --netif_add eth0 --save
```
Set the diskspace: 
```
sudo vzctl set ltsp-root01 --diskspace 10G --save
```
Start the VZ:
```
sudo vzctl start ltsp-root01
```
Enter the VZ: 
```
sudo vzctl enter ltsp-root01
```
Add these two entries to your sources.list if it does not exist yet:
```
deb http://ppa.launchpad.net/stgraber/ubuntu trusty main restricted universe multiverse
```
Configure /etc/network/interfaces using 192.168.0.2:
```
auto lo
iface lo inet loopback
auto eth0
iface eth0 inet static
 address 192.168.0.2
 netmask 255.255.255.0
 gateway 192.168.0.1
 ```
Set the DNS server in /etc/resolvconf/resolv.conf.d/base`:
```
search lan
nameserver 208.67.222.222
nameserver 208.67.220.220
```
Apply changes with:
```
sudo resolvconf -u
```
Update the VZ:
```
sudo apt-get update
```
Install tftpd-hpa:
```
sudo apt-get install tftpd-hpa
```
Install ltsp-server and isc-dhcp-server: 
```
sudo apt-get install ltsp-server isc-dhcp-server --no-install-recommends
```
Now, you must edit the DHCP server configuration file `/etc/dhcp/dhcpd.conf` adding:
```
ddns-update-style none;
default-lease-time 600;
max-lease-time 7200;
authoritat
log-facility local7;
subnet 192.168.0.0 netmask 255.255.255.0 {
  option domain-name "lan";
  option domain-name-servers 208.67.222.222, 208.67.220.220;
  option routers 192.168.0.1;
  range 192.168.0.100 192.168.0.254;
  next-server 192.168.0.2;
  filename "/ltsp/i386/pxelinux.0";
}
```
Finally, you have to make sure that the file `/etc/default/isc-dhcp-server` has the following line, which will set the isc-dhcp-server to listen on the host-only inteface (eth0) to serve IPs:
```
INTERFACES="eth0"
```
Restart isc-dhcp-server:
```
sudo /etc/init.d/isc-dhcp-server restart
```
If the command above fail, you probably have erros on `/etc/default/isc-dhcp-server`. See the log /var/log/syslog. You can also test if the isc-dhcp-server is working properly by lauching a thin client virtual machine (you'll be able to see it getting an IP address in the specified range).

## Build Chroot
Thin clients need 32-bit chroot. First, make sure you have squashfs-tools and nbd-server installed:
```
sudo apt-get update && sudo apt-get install squashfs-tools 
sudo apt-get install nbd-server
```
Now, build the client:
```
sudo ltsp-build-client --arch i386 --ltsp-cluster --prompt-rootpass --accept-unsigned-packages
```
When asked for ltsp-cluster settings answer as follow:
```
Server name: 192.168.1.3
Port (default: 80): 80
Use SSL [y/N]: N
Enable hardware inventory [Y/n]: Y
Request timeout (default: 2): 2
```
Root user password for chroot will be asked, too.
```
Enter new UNIX password: 
Retype new UNIX password: 
passwd: password updated successfully
```
Your answered setup is in this file `/opt/ltsp/i386/etc/ltsp/getltscfg-cluster.conf`.

The VZ is ready, you can exit and continue with the next one.

# Create ltsp-control01 (Control center)
Create the VZ: 
```
sudo vzctl create 102 --ostemplate ubuntu-14.04-amd64-server --hostname ltsp-control01 -config basic
```
Set the VZ name: 
```
sudo vzctl set 102 --name ltsp-control01 --save
```
Add a network card: 
```
sudo vzctl set ltsp-control01 --netif_add eth0 --save
```
Start the VZ: 
```
sudo vzctl start ltsp-control01
```
Enter the VZ: 
```
sudo vzctl enter ltsp-control01
```
Configure /etc/network/interfaces using 192.168.0.3
```
auto lo
iface lo inet loopback
auto eth0
iface eth0 inet static
 address 192.168.0.3
 netmask 255.255.255.0
 gateway 192.168.0.1
 ```
Set the DNS server in /etc/resolvconf/resolv.conf.d/base`:
```
search lan
nameserver 208.67.222.222
nameserver 208.67.220.220
```
Apply changes with:
```
sudo resolvconf -u
```
Initialize the interface: 
```
ifup eth0
```
Update the VZ:
```
sudo apt-get update
```
Install ltsp-cluster-control postgresql: 
```
sudo apt-get install ltsp-cluster-control postgresql --no-install-recommends
```
If you get any error regarding apache2 while installing lts-cluster-control, please try [this](#Apache-Won't-start). After troubleshooting, execute the command below to make sure ltsp-cluster-control has installed succesfully:
```
sudo apt-get install --reinstall ltsp-cluster-control postgresql --no-install-recommends
```
Modify ltsp-cluster-control's configuration. Open `/etc/ltsp/ltsp-cluster-control.config.php` and make sure it looks like below:
```
<?php
    $CONFIG['save'] = "Save";
    $CONFIG['lang'] = "en"; #Language for the interface (en and fr are supported"
    $CONFIG['charset'] = "UTF-8";
    $CONFIG['use_https'] = "false"; #Force https
    $CONFIG['terminal_auth'] = "false";
    $CONFIG['db_server'] = "localhost"; #Hostname of the database server
    $CONFIG['db_user'] = "ltsp"; #Username to access the database
    $CONFIG['db_password'] = "ltsp"; #Password to access the database
    $CONFIG['db_name'] = "ltsp"; #Database name
    $CONFIG['db_type'] = "postgres"; #Database type (only postgres is supported)
    $CONFIG['auth_name'] = "EmptyAuth";
    $CONFIG['loadbalancer'] = "192.168.0.4"; #Hostname of the loadbalancer
    $CONFIG['first_setup_lock'] = "TRUE";
    $CONFIG['printer_servers'] = array("cups.yourdomain.com"); #Hostname(s) of your print servers
    $CONFIG['rootInstall'] = "/usr/share/ltsp-cluster-control/Admin/";
?>
```
Create a new user for the database. Use the same password as above (db_password = ltsp)
```
sudo -u postgres createuser -SDRIP ltsp
Enter password for new role: 
Enter it again:
``` 
Create a new database.
```
sudo -u postgres createdb ltsp -O ltsp
```
Move to the new directory and create tables in database. You'll be prompted for the user's password:
```
cd /usr/share/ltsp-cluster-control/DB/
cat schema.sql functions.sql | psql -h localhost ltsp ltsp
Password for user ltsp: 
```
Now you have to act as a root user and move to the /root directory:
```
sudo su
cd /root
```
Get two files for database:
```
wget --no-check-certificate --content-disposition https://github.com/flpmat/ltsp-cluster-openvz/blob/master/files/control-center.py
```
```
wget --no-check-certificate --content-disposition https://github.com/flpmat/ltsp-cluster-openvz/blob/master/files/rdp%2Bldm.config
```
Modify the `control-center.py` file you just downloaded, using the same information for database:
```
#/usr/bin/python
import pgdb, os, sys

#FIXME: This should be a configuration file
db_user="ltsp"
db_password="ltsp"
db_host="localhost"
db_database="ltsp"
```
Install python postgresql support: 
```
apt-get install python-pygresql
``` 
Stop Apache2 and install two files:
```
/etc/init.d/apache2 stop
python control-center.py rdp+ldm.config
```
Add the following line to the end of `/etc/apache2/apache2.conf` file:
```
Include conf.d/*.conf
```
Start Apache2 again.
```
/etc/init.d/apache2 start
```
Stop acting like a root user.
```
exit
```
Install Xorg and Firefox:
```
sudo apt-get install xorg
sudo apt-get install firefox
```
Open your Firefox and go to the admin web page on http://ltsp-root01/ltsp-cluster-control/Admin/admin.php.
```
startx
firefox
```
In the first page (“Configuration”) make a few changes, this way:
```
LANG = en_EN.UTF-8
LDM_DIRECTX = True
LDM_SERVER = %LOADBALANCER%
LOCAL_APPS_MENU = True
SCREEN_07 = ldm
TIMESERVER = ntp.ubuntu.com
XKBLAYOUT = en
```
In the tab Nodes, create a new node by clicking the button Create Child and then typiyng the name of your node (name it appserv01).

The VZ is ready, you can exit and continue with the next one.

# Create ltsp-loadbalancer01 (Load Balancer)
Create the VZ: 
```
sudo vzctl create 103 --ostemplate ubuntu-14.04-amd64-server --hostname ltsp-loadbalancer01 -config basic
```
Set the VZ name: 
```
sudo vzctl set 103 --name ltsp-loadbalancer01 --save
```
Add a network card: 
```
sudo vzctl set ltsp-loadbalancer01 --netif_add eth0 --save
```
Start the VZ: 
```
sudo vzctl start ltsp-loadbalancer01
```
Enter the VZ: 
```
sudo vzctl enter ltsp-loadbalancer01
```
Configure /etc/network/interfaces using 192.168.0.4:
```
auto lo
iface lo inet loopback
auto eth0
iface eth0 inet static
 address 192.168.0.4
 netmask 255.255.255.0
 gateway 192.168.0.1
 ```
Set the DNS server in `/etc/resolvconf/resolv.conf.d/base`:
```
search lan
nameserver 208.67.222.222
nameserver 208.67.220.220
```
Apply changes with:
```
sudo resolvconf -u
```
Initialize the interface: 
```
ifup eth0
```
Update the VZ:
```
sudo apt-get update
```
Install ltsp-cluster-lbserver: 
```
sudo apt-get install ltsp-cluster-lbserver --no-install-recommends
```
Configure `/etc/ltsp/lbsconfig.xml` like below:
```
<?xml version="1.0"?>
<lbsconfig>
    <lbservice listen="*:8008" max-threads="1" refresh-delay="60" returns="$IP"/>
    <lbslave is-slave="false"/>
    <mgmtservice enabled="true" listen="*:8001"/>
    <nodes>
        <group default="true" name="trusty">
            <node address="http://192.168.0.5:8000" name="appserv01"/>
        </group>
    </nodes>
    <rules>
        <variable name="LOADAVG" weight="50">
            <rule capacity=".7"/>
        </variable>
        <variable name="NBX11SESS" weight="25">
            <rule capacity="$CPUFREQ*$CPUCOUNT*$CPUCOUNT/120" critical="$CPUFREQ*$CPUCOUNT*$CPUCOUNT/100"/>
        </variable>
        <variable name="MEMUSED" weight="25">
            <rule capacity="$MEMTOTAL-100000"/>
        </variable>
    </rules>
</lbsconfig>
```
The configuration above says we have 1 application server of name appserv01 running in VZ of IP 192.168.0.5.

Restart the loadbalancer: 
```
/etc/init.d/ltsp-cluster-lbserver restart
```
The VZ is ready, you can exit and continue with the next one.

# Create ltsp-appserv01 (First Application Server)
Create the VZ: 
```
sudo vzctl create 104 --ostemplate ubuntu-14.04-amd64-server --hostname ltsp-appserv01 -config basic
```
Set the VZ name: 
```
sudo vzctl set 104 --name ltsp-appserv01 --save
```
Set the disk limit: 
```
vzctl set ltsp-appserv01 --diskspace 5G --save
```
Allow fuse device: 
```
vzctl set ltsp-appserv01 --devices c:10:229:rw --save
```
Add a network card: 
```
sudo vzctl set ltsp-appserv01 --netif_add eth0 --save
```
Set all UBC parameters to "unlimited" in: 
```
/etc/vz/names/ltsp-appserv01
```
Start the VZ: 
```
sudo vzctl start ltsp-appserv01
```
Enter the VZ: 
```
sudo vzctl enter ltsp-appserv01
```
Configure `/etc/network/interfaces` using 192.168.0.5:
```
auto lo
iface lo inet loopback
auto eth0
iface eth0 inet static
 address 192.168.0.5
 netmask 255.255.255.0
 gateway 192.168.0.1
```
Set the DNS server in `/etc/resolvconf/resolv.conf.d/base`:
```
search lan
nameserver 208.67.222.222
nameserver 208.67.220.220
```
Apply changes with:
```
sudo resolvconf -u
```
Initialize the interface: 
```
ifup eth0
```
Update the VZ:
```
sudo apt-get update
```
Install ubuntu-desktop, ltsp-server, ltsp-cluster-lbagent and ltsp-cluster-accountmanager: 
```
apt-get install ubuntu-desktop ltsp-server ltsp-cluster-lbagent ltsp-cluster-accountmanager
```
If you get dpkg errors from the command above that leaves some packages uninstalled, run the following lines:
```
sudo apt-get autoremove
sudo apt-get update
sudo apt-get upgrade
sudo apt-get dist-upgrade
```
Remove network-manager: 
```
apt-get remove --purge network-manager
```
Remove some useless recommends: 
```
apt-get remove --purge gnome-orca xscreensaver
```
Make sure the system is clean: 
```
apt-get autoremove && apt-get autoclean
```
Disable nbd-server: 
```
update-rc.d -f nbd-server remove
```
Disable gdm: 
```
update-rc.d -f gdm remove
```
Disable bluetooth: 
```
update-rc.d -f bluetooth remove
```
Disable pulseaudio:
```
update-rc.d -f pulseaudio remove
```
Create the file `/etc/xdg/autostart/pulseaudio-module-suspend-on-idle.desktop`:
```
[Desktop Entry]
Version=1.0
Encoding=UTF-8
Name=PulseAudio Session Management
Comment=Load module-suspend-on-idle into PulseAudio
Exec=pactl load-module module-suspend-on-idle
Terminal=false
Type=Application
Categories=
GenericName=
```
Add a `demo` user:
```
adduser demo
adduser demo fuse
adduser demo audio
adduser demo video
```
Create fuse device: 
```
mknod /dev/fuse c 10 229
```
Set access rights on fuse: 
```
chown root.fuse /dev/fuse
```
Set access rights on fuse: 
```
chmod 660 /dev/fuse
```
Fix FUSA not loading (defaults): 
```
gconftool-2 --direct --config-source xml:readwrite:/etc/gconf/gconf.xml.defaults --set --type list --list-type string /apps/panel/global/disabled_applets "[OAFIID:GNOME_FastUserSwitchApplet]"
```
Disable lock screen (always): 
```
gconftool-2 --direct --config-source xml:readwrite:/etc/gconf/gconf.xml.mandatory --set --type boolean /desktop/gnome/lockdown/disable_lock_screen True
```
Disable the screensaver (always): 
```
gconftool-2 --direct --config-source xml:readwrite:/etc/gconf/gconf.xml.mandatory --set --type boolean /apps/gnome_settings_daemon/screensaver/start_screensaver False
```
Disable DPMS in gnome-power-manager (defaults): 
```
gconftool-2 --direct --config-source xml:readwrite:/etc/gconf/gconf.xml.defaults --set --type integer /apps/gnome-power-manager/timeout/sleep_display_ac 0
```
The VZ is ready, you can then reboot the host to make sure everything restarts properly.

# Running

Once you start all containers, the `/var/log/ltsp-cluster-lbserver.log` file in the root server should look like this:
![LTSP Log](https://github.com/flpmat/ltsp-cluster-openvz/blob/master/images/ltsp-log.png)

Turn on your Thin Client machine. As this computer is not assigned to a node yet, it will show the following screen upon successful boot:
![Thin Client Info](https://github.com/flpmat/ltsp-cluster-openvz/blob/master/images/thin-client-info.png)

To add the thin client computer to a node, open the ltsp-cluster control center and go to the tab `Nodes`. Change to AppServ01 node, select the computer on the list and click on Add to AppServ01:

![Step 1](https://github.com/flpmat/LTSP-Cluster-Tutorial/blob/master/images/add%20to%20app%201.png)
![Step 2](https://github.com/flpmat/LTSP-Cluster-Tutorial/blob/master/images/move%20to%20app%202.png)

[Click here](https://www.youtube.com/watch?v=7QdYW-NT_sw) for more detailed instructions.

# Troubleshoot

## Error on screen_session

You may encouter the following error upon your thin client boot:
```
./screen_session: 48: [: Illegal number:
./screen_session: 78: ./screen_session: /usr/share/ltsp/screen.d/: Permission denied
```
To fix this, substitute the content of the file `/opt/ltsp/i386/usr/share/ltsp/screen_session` with the content below:
```
#!/bin/sh
#
#  Copyright (c) 2002 McQuillan Systems, LLC
#
#  Author: James A. McQuillan <jam@McQuil.com>
#
#  2005, Matt Zimmerman <mdz@canonical.com>
#  2006, Oliver Grawert <ogra@canonical.com>
#  2007, Scott Balneaves <sbalneav@ltsp.org>
#  2008, Warren Togami <wtogami@redhat.com>
#        Stephane Graber <stgraber@ubuntu.com>
#        Vagrant Cascadian <vagrant@freegeek.org>
#        Gideon Romm <ltsp@symbio-technologies.com>
#  2012, Alkis Georgopoulos <alkisg@gmail.com>
#  2014, Maximiliano Boscovich <maximiliano@boscovich.com.ar>
#  
#  This program is free software; you can redistribute it and/or
#  modify it under the terms of the GNU General Public License as
#  published by the Free Software Foundation; either version 2 of the
#  License, or (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with this program.  If not, you can find it on the World Wide
#  Web at http://www.gnu.org/copyleft/gpl.html, or write to the Free
#  Software Foundation, Inc., 51 Franklin St, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#

# Load LTSP configuration
# ltsp_config sources ltsp-client-functions
. /usr/share/ltsp/ltsp_config

case "$1" in
    [0-1][0-9])
        export SCREEN_NUM="$1"
        ;;
    *)
        die "Usage: $0 [01..12]"
        ;;
esac

while true; do
    # Wait until this is the active vt before launching the screen script
    while [ $(fgconsole) -ne "$SCREEN_NUM" ]; do
        sleep 2
    done

    if [ -f /etc/ltsp/getltscfg-cluster.conf ]; then
        # Reset the environement
        unset $(env | egrep '^(\w+)=(.*)$' | egrep -vw 'PWD|USER|PATH|HOME|SCREEN_NUM' | /usr/bin/cut -d= -f1)
        . /usr/share/ltsp/ltsp_config
        eval $(getltscfg-cluster -a -l prompt)
    fi

    read script args <<EOF
$(eval echo "\$SCREEN_$SCREEN_NUM")
EOF

    # Screen scripts in /etc override those in /usr
    unset script_path
    for dir in /etc/ltsp/screen.d /usr/share/ltsp/screen.d; do
        if [ -x "$dir/$script" ]; then
            script_path="$dir/$script"
            break
        fi
    done
    if [ -z "$script_path" ]; then
        die "Script '$script' for SCREEN_$SCREEN_NUM was not found"
    fi

    for script in $(run_parts_list /usr/share/ltsp/screen-session.d/ S); do
        . "$script"
    done
    "$script_path" "$args"
    for script in $(run_parts_list /usr/share/ltsp/screen-session.d/ K); do
        . "$script"
    done
done
```
After that, update the ltsp image:
```
ltsp-update-image i386
```

## Apache Won't start
Check the log file `/var/log/apache2/error.log`. If the error is `Fatal Error Unable to allocate shared memory` you'll have to check the file `/proc/user_beancounters`. Check which resources have values greater than 0 at the failcnt column. The field failcnt shows the number of refused “resource allocations” for the whole lifetime of the process group (https://wiki.openvz.org/Proc/user_beancounters).
If `privvmpages` has failcnt greater than 0, exit the container (`exit`) and increase the container's memory:
```
vzctl set ${cid} --vmguarpages 64M --save
vzctl set ${cid} --oomguarpages 64M --save
vzctl set ${cid} --privvmpages 64000:128000 --save
``` 
If `shmpages` has failcnt greater than 0, increase it by using:
```
vzctl set ${cid} --shmpages 40960 --save
```
Restart the VPS and then enter. Check if the Apache2 service is working properly by starting it:
```
sudo /etc/init.d/apache2 start
```
You should get no errors at this point.

# References
* [UbuntuLTSP/LTSP-Cluster Tutorial](https://help.ubuntu.com/community/UbuntuLTSP/LTSP-Cluster)
* [control-center.py (original file)](http://bazaar.launchpad.net/%7Eltsp-cluster-team/ltsp-cluster/ltsp-cluster-control\/download/head%3A/controlcenter.py-20090118065910-j5inpmeqapsuuepd-3/control-center.py)
* [rdp-ldm.config (original file)](http://bazaar.launchpad.net/%7Eltsp-cluster-team/ltsp-cluster/ltsp-cluster-control\/download/head%3A/rdpldm.config-20090430131602-g0xccqrcx91oxsl0-1/rdp%2Bldm.config)
* [OpenVZ GPG Key (original file)](http://ftp.openvz.org/debian/archive.key)
