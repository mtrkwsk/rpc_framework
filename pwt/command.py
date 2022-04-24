import uuid


def command(cmd, **kwargs):
    cid = uuid.uuid1().hex[4:12]
    c = {'cmd': cmd,
         'cid': cid,
         'args': kwargs}
    return c

def parse_command(cmd):
    # TODO: Sanity check
    # !!!! , extra={'cid': cmd['cid']}
    # s = json.loads
    if 'cid' not in cmd:
        cmd['cid'] = None


    return cmd