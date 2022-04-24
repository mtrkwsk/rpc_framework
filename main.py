import pwt_config
from pwt.pwtComponent import PwtComponent



if __name__ == '__main__':
    pwt = PwtComponent()
    pwt.put_command(pwt_config.commands)
    pwt.start()
