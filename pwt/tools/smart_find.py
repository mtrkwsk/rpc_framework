def smart_find(l : list, phrase):
    """Tries to find phrase in list and return matched name (unchanged)."""
    # try:
    #     e = l[0]
    # except IndexError:
    #     return None
    # print (f"{e.lower()} {phrase.lower()}")

    for c in l:
        if c == phrase:
            return c
    print(f"Warning: exact component {phrase} match not found. Searching similar names...")

    for c in l:
        if c.lower() == phrase.lower():
            print(f"Warning: Found similar component: {c}")
            return c

    for c in l:
        if phrase.lower() in c.lower():
            print(f"Warning: Found similar component: {c}")
            return c

    for c in l:
        if c.lower() in phrase.lower() :
            print(f"Warning: Found similar component: {c}")
            return c

    print("Warning: similar component not found.")
    return None


if __name__ == '__main__':
    l = ['component', 'component_2312ca', 'tx_v2x', "RX_nuc"]
    v = smart_find(l, 'rx')
    print(v)