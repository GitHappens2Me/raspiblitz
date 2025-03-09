#!/usr/bin/python3

import sys
import subprocess
#TODO add option to actually DELETE (not just deactivate) Watchtower (problably deleting the Database entry)

#TODO Maybe Use Blitzerror for Exceptionmanagment. like in blitz.subscriptions.letsencrypt.py
def handleException(e):
    if isinstance(e, BlitzError):
        #eprint(e.errorLong)
        #eprint(e.errorException)
        print("error='{0}'".format(e.errorShort))
    else:
        eprint(e)
        print("error='{0}'".format(str(e)))
    sys.exit(1)


def add_watchtower():
    try:
        if len(sys.argv) <= 2:
            raise ValueError("Missing URI parameter")
            
        uri = sys.argv[2]
        
        result = subprocess.run(
            ['lncli', 'wtclient', 'add', uri],
            capture_output=True,
            text=True,
            check=True
        )
        # Explicit success exit
        sys.exit(0)
        
    except subprocess.CalledProcessError as e:
        print(f"Error adding watchtower: {e.stderr}")
        sys.stderr.write(f"LNCLI Error: {e.stderr}\n")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)

def remove_watchtower():
    try:
        if len(sys.argv) <= 2:
            raise ValueError("Missing URI parameter")
            
        pubkey = sys.argv[2]
        
        result = subprocess.run(
            ['lncli', 'wtclient', 'remove', pubkey],
            capture_output=True,
            text=True,
            check=True
        )
        sys.exit(0)
        
    except subprocess.CalledProcessError as e:
        print(f"Error removing watchtower: {e.stderr}")
        sys.stderr.write(f"LNCLI Error: {e.stderr}\n")
        sys.exit(1)
    except Exception as e:
        print(f"Error: {str(e)}")
        sys.stderr.write(f"Error: {str(e)}\n")
        sys.exit(1)


def list_towers():
    try:
        result = subprocess.run(
            ['lncli', 'wtclient', 'towers'],
            capture_output=True,
            text=True,
            check=True
        )
        # Directly output the raw JSON result to stdout
        print(result.stdout)
        sys.exit(0)
        
    except subprocess.CalledProcessError as e:
        print(f"LNCLI Error: {e.stderr.strip()}")
        sys.stderr.write(f"Command failed: {e.cmd}\n")
        sys.exit(1)
    except Exception as e:
        print(f"Unexpected Error: {str(e)}")
        sys.stderr.write(f"Traceback: {traceback.format_exc()}\n")
        sys.exit(1)

#TODO use configparser (configparser duplicates with other lines of the config if they do not have spaces around the '=')
#TODO this doesnt delete the setting if wtclient.active=0
#TODO make this more concise
def activate_watchtower_client():
    """
    Exit codes:
    0 - No changes needed
    1 - Changes made, restart required
    2 - Error occurred
    """
    file_path = '/mnt/hdd/lnd/lnd.conf'
    try:
        with open(file_path, 'r') as f:
            lines = f.readlines()

        needs_restart = False
        wtclient_section_found = False
        wtclient_active_found = False
        in_wtclient_section = False

        for i, line in enumerate(lines):
            stripped = line.strip()
            
            # Detect section headers
            if stripped.startswith('[') and stripped.endswith(']'):
                section_name = stripped[1:-1]
                in_wtclient_section = (section_name == 'Wtclient')
                if in_wtclient_section:
                    wtclient_section_found = True
                continue

            if in_wtclient_section:
                if line.strip().startswith('wtclient.active'):
                    # Split on first occurrence of '='
                    parts = line.split('=', 1)
                    if len(parts) == 2:
                        current_value = parts[1].strip()
                        if current_value != '1':
                            # Preserve original formatting before '='
                            lines[i] = f"{parts[0].rstrip()}=1\n"
                            needs_restart = True
                    else:
                        # Malformed line - replace completely
                        lines[i] = 'wtclient.active=1\n'
                        needs_restart = True
                    wtclient_active_found = True

        # Add missing section/options if needed
        if not wtclient_section_found:
            lines.append('\n[Wtclient]\nwtclient.active=1\n')
            needs_restart = True
        elif not wtclient_active_found:
            # Find where to insert in existing section
            for i, line in enumerate(lines):
                if line.strip() == '[Wtclient]':
                    insert_pos = i + 1
                    # Find end of section
                    while insert_pos < len(lines):
                        if lines[insert_pos].strip().startswith('['):
                            break
                        insert_pos += 1
                    lines.insert(insert_pos, 'wtclient.active=1\n')
                    needs_restart = True
                    break

        if needs_restart:
            with open(file_path, 'w') as f:
                f.writelines(lines)
            sys.exit(1)
        else:
            sys.exit(0)

    except Exception as e:
        print(f"Unexpected error: {str(e)}", file=sys.stderr)
        sys.exit(2)


def main():

    if sys.argv[1] == "add-watchtower":
        add_watchtower()
    elif sys.argv[1] == "activate-watchtower-client":
        activate_watchtower_client()
    elif sys.argv[1] == "list-towers":
        list_towers()
    elif sys.argv[1] == "remove-watchtower":
        remove_watchtower()
    else:
        print("# unknown command")


if __name__ == '__main__':
    main()
