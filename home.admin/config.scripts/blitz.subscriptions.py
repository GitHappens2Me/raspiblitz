#!/usr/bin/python3

########################################################
# SSH Dialogs to manage Subscriptions on the RaspiBlitz
########################################################

import os
import subprocess
import sys
import time
from datetime import datetime

import toml
sys.path.append('/home/admin/raspiblitz/home.admin/BlitzPy/blitzpy')
from config import RaspiBlitzConfig
from dialog import Dialog

# constants for standard services
SERVICE_LND_REST_API = "LND-REST-API"
SERVICE_LND_GRPC_API = "LND-GRPC-API"
SERVICE_LNBITS = "LNBITS"
SERVICE_BTCPAY = "BTCPAY"

# load config 
cfg = RaspiBlitzConfig()
cfg.reload()

# basic values
SUBSCRIPTIONS_FILE = "/mnt/hdd/app-data/subscriptions/subscriptions.toml"


#######################
# HELPER FUNCTIONS
#######################

# ToDo(frennkie) these are not being used!

def eprint(*args, **kwargs):
    print(*args, file=sys.stderr, **kwargs)


def parse_date_ip2tor(date_str):
    return datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%fZ")


def seconds_left(date_obj):
    return round((date_obj - datetime.utcnow()).total_seconds())


#######################
# SSH MENU FUNCTIONS
#######################

def my_subscriptions():
    # check if any subscriptions are available
    count_subscriptions = 0
    try:
        os.system("sudo chown admin:admin {0}".format(SUBSCRIPTIONS_FILE))
        subs = toml.load(SUBSCRIPTIONS_FILE)
        if 'subscriptions_ip2tor' in subs:
            count_subscriptions += len(subs['subscriptions_ip2tor'])
        if 'subscriptions_letsencrypt' in subs:
            count_subscriptions += len(subs['subscriptions_letsencrypt'])
    except Exception as e:
        print(f"warning: {e}")

    if count_subscriptions == 0:
        Dialog(dialog="dialog", autowidgetsize=True).msgbox('''
You have no active or inactive subscriptions.
            ''', title="Info")
        return

    # load subscriptions and make dialog choices out of it
    choices = []
    lookup = {}
    lookup_index = 0
    subs = toml.load(SUBSCRIPTIONS_FILE)

    # list ip2tor subscriptions
    if 'subscriptions_ip2tor' in subs:
        for sub in subs['subscriptions_ip2tor']:
            # remember subscription under lookupindex
            lookup_index += 1
            lookup[str(lookup_index)] = sub
            # add to dialog choices
            if sub['active']:
                active_state = "active"
            else:
                active_state = "in-active"
            name = "IP2TOR Bridge (P:{1}) for {0}".format(sub['name'], sub['port'])
            choices.append(("{0}".format(lookup_index), "{0} ({1})".format(name.ljust(30), active_state)))

    # list letsencrypt subscriptions
    if 'subscriptions_letsencrypt' in subs:
        for sub in subs['subscriptions_letsencrypt']:
            # remember subscription under lookupindex
            lookup_index += 1
            lookup[str(lookup_index)] = sub
            # add to dialog choices
            if sub['active']:
                active_state = "active"
            else:
                active_state = "in-active"
            name = "LETSENCRYPT {0}".format(sub['id'])
            choices.append(("{0}".format(lookup_index), "{0} ({1})".format(name.ljust(30), active_state)))

    # show menu with options
    d = Dialog(dialog="dialog", autowidgetsize=True)
    d.set_background_title("RaspiBlitz Subscriptions")
    code, tag = d.menu(
        "\nYou have the following subscriptions - select for details:",
        choices=choices, cancel_label="Back", width=65, height=15, title="My Subscriptions")

    # if user chooses CANCEL
    if code != d.OK:
        return

    # get data of selected subscription
    selected_sub = lookup[str(tag)]

    # show details of selected
    d = Dialog(dialog="dialog", autowidgetsize=True)
    d.set_background_title("My Subscriptions")
    if selected_sub['type'] == "letsencrypt-v1":
        if len(selected_sub['warning']) > 0:
            selected_sub['warning'] = "\n{0}".format(selected_sub['warning'])
        text = '''
This is a LetsEncrypt subscription using the free DNS service
{dnsservice}

It allows using HTTPS for the domain:
{domain}

The domain is pointing to the IP:
{ip}

The state of the subscription is: {active} {warning}

The following additional information is available:
{description}

'''.format(dnsservice=selected_sub['dnsservice_type'],
           domain=selected_sub['id'],
           ip=selected_sub['ip'],
           active="ACTIVE" if selected_sub['active'] else "NOT ACTIVE",
           warning=selected_sub['warning'],
           description=selected_sub['description']
           )

    elif selected_sub['type'] == "ip2tor-v1":
        if len(selected_sub['warning']) > 0:
            selected_sub['warning'] = "\n{0}".format(selected_sub['warning'])
        text = '''
This is a IP2TOR subscription bought on {initdate} at
{shop}

It forwards from the public address {publicaddress} to
{toraddress}
for the RaspiBlitz service: {service}

It will renew every {renewhours} hours for {renewsats} sats.
Total payed so far: {totalsats} sats

The state of the subscription is: {active} {warning}

The following additional information is available:
{description}
'''.format(initdate=selected_sub['time_created'],
           shop=selected_sub['shop'],
           publicaddress="{0}:{1}".format(selected_sub['ip'], selected_sub['port']),
           toraddress=selected_sub['tor'],
           renewhours=(round(int(selected_sub['duration']) / 3600)),
           renewsats=(round(int(selected_sub['price_extension']) / 1000)),
           totalsats=(round(int(selected_sub['price_total']) / 1000)),
           active="ACTIVE" if selected_sub['active'] else "NOT ACTIVE",
           warning=selected_sub['warning'],
           description=selected_sub['description'],
           service=selected_sub['name']
           )
    else:
        text = "no text?! FIXME"

    if selected_sub['active']:
        extra_label = "CANCEL SUBSCRIPTION"
    else:
        extra_label = "DELETE SUBSCRIPTION"
    code = d.msgbox(text, title="Subscription Detail", ok_label="Back", extra_button=True, extra_label=extra_label,
                    width=75, height=30)

    # user wants to delete this subscription
    # call the responsible sub script for deletion just in case any subscription needs to do some extra
    # api calls when canceling
    if code == "extra":
        os.system("clear")
        if selected_sub['type'] == "letsencrypt-v1":
            cmd = "python /home/admin/config.scripts/blitz.subscriptions.letsencrypt.py subscription-cancel {0}".format(
                selected_sub['id'])
            print("# running: {0}".format(cmd))
            os.system(cmd)
            time.sleep(2)
        elif selected_sub['type'] == "ip2tor-v1":
            cmd = "python /home/admin/config.scripts/blitz.subscriptions.ip2tor.py subscription-cancel {0}".format(
                selected_sub['id'])
            print("# running: {0}".format(cmd))
            os.system(cmd)
            time.sleep(2)
        else:
            print("# FAIL: unknown subscription type")
            time.sleep(3)

    # loop until no more subscriptions or user chooses CANCEL on subscription list
    my_subscriptions()


def check_and_enable_wtclient():
    config_path = "/home/bitcoin/.lnd/lnd.conf"
    needs_restart = False
    
    try:
        # Read current config
        with open(config_path, 'r') as f:
            lines = f.readlines()

        # Parse config
        wtclient_section = False
        active_setting = False
        new_lines = []
        
        for line in lines:
            stripped = line.strip()
            
            # Detect section
            if stripped == "[Wtclient]":
                wtclient_section = True
                new_lines.append(line)
            elif stripped.startswith("["):
                wtclient_section = False
                new_lines.append(line)
            else:
                # Check for setting in section
                if wtclient_section:
                    if stripped.startswith("wtclient.active"):
                        if "=1" in stripped:
                            active_setting = True
                        new_lines.append("wtclient.active=1\n")
                    else:
                        new_lines.append(line)
                else:
                    new_lines.append(line)

        # Add section if missing
        if not "[Wtclient]" in lines:
            new_lines.append("\n[Wtclient]\n")
            new_lines.append("wtclient.active=1\n")
            needs_restart = True
        elif not active_setting:
            new_lines.append("wtclient.active=1\n")
            needs_restart = True

        # Write back if changes needed
        if needs_restart:
            with open(config_path, 'w') as f:
                f.writelines(new_lines)
            print("Enabled wtclient in lnd.conf")
            
            # Restart LND
            subprocess.run(["sudo", "systemctl", "restart", "lnd"])
            print("Restarted LND to apply changes")
            time.sleep(5)  # Wait for LND to restart

        return True
    
    except Exception as e:
        print(f"Error modifying lnd.conf: {str(e)}")
        return False


def main():
    #######################
    # SSH MENU
    #######################

    choices = list()
    choices.append(("LIST", "My Subscriptions"))
    choices.append(("NEW1", "+ IP2TOR Bridge (paid)"))
    choices.append(("NEW2", "+ LetsEncrypt HTTPS Domain (free)"))
    choices.append(("NEW3", "+ Watchtower Subscription"))

    d = Dialog(dialog="dialog", autowidgetsize=True)
    d.set_background_title("RaspiBlitz Subscriptions")
    code, tag = d.menu(
        "\nCheck existing subscriptions or create new:",
        choices=choices, width=50, height=10, title="Subscription Management")

    # if user chooses CANCEL
    if code != d.OK:
        sys.exit(0)

    #######################
    # MANAGE SUBSCRIPTIONS
    #######################

    if tag == "LIST":
        my_subscriptions()
        sys.exit(0)

    ###############################
    # NEW LETSENCRYPT HTTPS DOMAIN
    ###############################

    if tag == "NEW2":
        # run creating a new IP2TOR subscription
        os.system("clear")
        cmd = "python /home/admin/config.scripts/blitz.subscriptions.letsencrypt.py create-ssh-dialog"
        print("# running: {0}".format(cmd))
        os.system(cmd)
        sys.exit(0)

    ###############################
    # NEW IP2TOR BRIDGE
    ###############################

    if tag == "NEW1":

        # check if Blitz is running behind TOR
        cfg.reload()
        if not cfg.run_behind_tor.value:
            Dialog(dialog="dialog", autowidgetsize=True).msgbox('''
    The IP2TOR service just makes sense if you
    run your RaspiBlitz behind TOR.
            ''', title="Info")
            sys.exit(0)

        os.system("clear")
        print("please wait ..")

        # check for which standard services already a active bridge exists
        lnd_rest_api = False
        lnd_grpc_api = False
        lnbits = False
        btcpay = False
        try:
            if os.path.isfile(SUBSCRIPTIONS_FILE):
                os.system("sudo chown admin:admin {0}".format(SUBSCRIPTIONS_FILE))
                subs = toml.load(SUBSCRIPTIONS_FILE)
                for sub in subs['subscriptions_ip2tor']:
                    if not sub['active']:
                        continue
                    if sub['active'] and sub['name'] == SERVICE_LND_REST_API:
                        lnd_rest_api = True
                    if sub['active'] and sub['name'] == SERVICE_LND_GRPC_API:
                        lnd_grpc_api = True
                    if sub['active'] and sub['name'] == SERVICE_LNBITS:
                        lnbits = True
                    if sub['active'] and sub['name'] == SERVICE_BTCPAY:
                        btcpay = True
        except Exception as e:
            print(e)

        # check if BTCPayServer is installed
        btc_pay_server = False
        status_data = subprocess.run(['/home/admin/config.scripts/bonus.btcpayserver.sh', 'status'],
                                     stdout=subprocess.PIPE).stdout.decode('utf-8').strip()
        if status_data.find("installed=1") > -1:
            btc_pay_server = True

        # ask user for which RaspiBlitz service the bridge should be used
        choices = list()
        choices.append(("REST", "LND REST API {0}".format("--> ALREADY BRIDGED" if lnd_rest_api else "")))
        choices.append(("GRPC", "LND gRPC API {0}".format("--> ALREADY BRIDGED" if lnd_grpc_api else "")))
        if cfg.lnbits:
            choices.append(("LNBITS", "LNbits Webinterface {0}".format("--> ALREADY BRIDGED" if lnbits else "")))
        if btc_pay_server:
            choices.append(("BTCPAY", "BTCPay Server Webinterface {0}".format("--> ALREADY BRIDGED" if btcpay else "")))
        choices.append(("SELF", "Create a custom IP2TOR Bridge"))

        d = Dialog(dialog="dialog", autowidgetsize=True)
        d.set_background_title("RaspiBlitz Subscriptions")
        code, tag = d.menu(
            "\nChoose RaspiBlitz Service to create Bridge for:",
            choices=choices, width=60, height=10, title="Select Service")

        # if user chooses CANCEL
        if code != d.OK:
            sys.exit(0)

        service_name = None
        tor_address = None
        tor_port = None
        if tag == "REST":
            # get TOR address for REST
            service_name = SERVICE_LND_REST_API
            tor_address = subprocess.run(['sudo', 'cat', '/mnt/hdd/tor/lndrest/hostname'],
                                         stdout=subprocess.PIPE).stdout.decode('utf-8').strip()
            tor_port = 8080
        if tag == "GRPC":
            # get TOR address for GRPC
            service_name = SERVICE_LND_GRPC_API
            tor_address = subprocess.run(['sudo', 'cat', '/mnt/hdd/tor/lndrpc/hostname'],
                                         stdout=subprocess.PIPE).stdout.decode('utf-8').strip()
            tor_port = 10009
        if tag == "LNBITS":
            # get TOR address for LNBits
            service_name = SERVICE_LNBITS
            tor_address = subprocess.run(['sudo', 'cat', '/mnt/hdd/tor/lnbits/hostname'],
                                         stdout=subprocess.PIPE).stdout.decode('utf-8').strip()
            tor_port = 443
        if tag == "BTCPAY":
            # get TOR address for BTCPAY
            service_name = SERVICE_BTCPAY
            tor_address = subprocess.run(['sudo', 'cat', '/mnt/hdd/tor/btcpay/hostname'],
                                         stdout=subprocess.PIPE).stdout.decode('utf-8').strip()
            tor_port = 443
        if tag == "SELF":
            service_name = "CUSTOM"
            try:
                # get custom TOR address
                code, text = d.inputbox(
                    "Enter TOR Onion-Address:",
                    height=10, width=60, init="",
                    title="IP2TOR Bridge Target")
                text = text.strip()
                os.system("clear")
                if code != d.OK:
                    sys.exit(0)
                if len(text) == 0:
                    sys.exit(0)
                if text.find('.onion') < 0 or text.find(' ') > 0:
                    print("Not a TOR Onion Address")
                    time.sleep(3)
                    sys.exit(0)
                tor_address = text
                # get custom TOR port
                code, text = d.inputbox(
                    "Enter TOR Port Number:",
                    height=10, width=40, init="80",
                    title="IP2TOR Bridge Target")
                text = text.strip()
                os.system("clear")
                if code != d.OK:
                    sys.exit(0)
                if len(text) == 0:
                    sys.exit(0)
                tor_port = int(text)
            except Exception as e:
                print(e)
                time.sleep(3)
                sys.exit(0)

        # run creating a new IP2TOR subscription
        os.system("clear")
        cmd = "python /home/admin/config.scripts/blitz.subscriptions.ip2tor.py create-ssh-dialog {0} {1} {2}".format(
            service_name, tor_address, tor_port)
        print("# running: {0}".format(cmd))
        os.system(cmd)

        sys.exit(0)

    ###############################
    # NEW WATCHTOWER SUBSCRIPTION
    ###############################
    if tag == "NEW3":
        d = Dialog(dialog="dialog", autowidgetsize=True)
    
        # Get watchtower URI from user
        code, uri = d.inputbox(
            "Enter Watchtower URI (pubkey@host:port):",
            height=10, 
            width=60,
            title="Watchtower Subscription"
        )
        if code != d.OK:
            return
        
        # Validate URI format (needs regex)
        #if not re.match(r'^[a-f0-9]{66}@([a-z0-9]+\.onion|\d+\.\d+\.\d+\.\d+):\d+$', uri):
        #    d.msgbox("Invalid format. Should be: pubkey@host:port\nExample: 03864ef025...@watchtower.com:9911",
        #            title="Error")
        #    return

        # Confirm subscription
        code = d.yesno(f"Subscribe to this watchtower?\n\n{uri}", 
                    title="Confirm Subscription")
        if code != d.OK:
            return
        
        if not check_and_enable_wtclient():
            return

        # Execute subscription command
        try:
            result = subprocess.run(
                ['lncli', 'wtclient', 'add', uri],
                capture_output=True,
                text=True,
                check=True
            )
            d.msgbox(f"Successfully subscribed to watchtower!\n\n{result.stdout}",
                    title="Success")
        except subprocess.CalledProcessError as e:
            d.msgbox(f"Failed to subscribe:\n\n{e.stderr}", 
                    title="Error")


if __name__ == '__main__':
    main()
