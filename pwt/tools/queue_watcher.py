import multiprocessing
import threading
import queue

def queue_watcher(q : multiprocessing.Queue):
    ''' Watches (observer) q in new thread and prints nicely its elements
    IMPORTANT: It pops element from queue, so it is removed permanently!
    '''
    def _watch(q, e):
        while not e.is_set():
            try:
                ret = q.get(timeout=1)
                print(ret)
            except queue.Empty:
                continue
            except KeyboardInterrupt:
                break
    e = multiprocessing.Event()
    t = threading.Thread(target=_watch, args=[q, e])
    t.start()
    return e