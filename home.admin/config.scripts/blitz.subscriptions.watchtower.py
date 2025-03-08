import sys
import subprocess

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



def activate_watchtower_client():
    file_path = '/mnt/hdd/lnd/lnd.conf'

    try:
        with open(file_path, 'r+') as f:
            lines = f.readlines()
            has_section = any(line.strip() == '[Wtclient]' for line in lines)
            has_setting = any(line.strip() == 'wtclient.active=1' for line in lines)

            if not has_setting:
                if not has_section:
                    lines.append('\n[Wtclient]\n')
                lines.append('wtclient.active=1\n')
                f.seek(0)
                f.writelines(lines)
                f.truncate()
    except Exception as e:
        print(f"Error modifying file: {e}")
        return False
    else:
        print("Successfully activated Wtclient" if not has_setting else "Wtclient already activated")
        return True




def main():

    if sys.argv[1] == "add-watchtower":
        add_watchtower()
    elif sys.argv[1] == "activate-watchtower-client":
        activate_watchtower_client()
    else:
        print("# unknown command")


if __name__ == '__main__':
    main()
