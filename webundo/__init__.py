#/usr/bin/env python
# -=- encoding: utf-8 -=-

"""This module implements Gmail's undo/cancel features, using Pylons or some
other web frameworks.

Here is a sample Pylons controller (called 'th', who knows why)::

.. code-block:: python
    from pylons import request, response, session, tmpl_context as c
    from YOURPROJECT.lib.base import BaseController, render

    import webundo

    class ThController(BaseController):
        def index(self):
            return render('th.mako')

        def save(self):
            # save the thing
            req = request
            def save():
                print "Writing to file..."
                open('/tmp/dump.txt', 'w').write(req.params.get('stuff'))
            c.key = webundo.launch_cancelable_job(save, 3)
            return render('saving.mako')

        def cancel(self, id):
            if webundo.cancel_job(id):
                return "Thread cancelled successfully"
            else:
                return "Too late, thread finished already."

        def publish(self):
            req = request
            def unpublish():
                print "Oops, let's unpublish", req.params.get('stuff')
                return "We're done"
            c.key = webundo.launch_undoable_job(unpublish, 10)
            c.published = request.params.get('stuff')
            print "Published stuff", c.published
            return render('publishing.mako')

        def undo(self, id):
            try:
                ret = undo_job(id)
            except webundo.ThreadLostError, e:
                return "Thread was lost already"
            return "Undone: %s" % ret


"""
import threading
from Queue import Empty, Queue
import uuid


__all__ = ['unproxy_closure', 'ThreadLostError', 'launch_cancelable_job',
           'launch_undoable_job', 'cancel_job', 'undo_job']

# Shared object, hopefully thread-safe :)
waiting_threads = {'cancelable_jobs': {},
                   'undoable_jobs': {},
                   }


class ThreadLostError(Exception):
    pass


def unproxy_closure(func):
    """Rewrite function with resolved closure references to proxy objects.

    It works with objects like StackedObjectProxy from Paste, which have
    a _current_obj() method.

    It could be extended to other frameworks or objects.
    """
    if not func.func_closure:
        return func
    import new
    def create_cell(obj):
        return (lambda: obj).func_closure[0]
    return new.function(func.func_code , func.func_globals, func.func_name,
                        func.func_defaults,
                        tuple(create_cell(cell.cell_contents._current_obj())
                                  if hasattr(cell.cell_contents, '_current_obj')
                                       and
                                     callable(cell.cell_contents._current_obj)
                                  else cell
                              for cell in func.func_closure))



def launch_cancelable_job(func, timeout):
    """Launch a new cancellable thread, and execute only after the timeout.

    This means, if someone calls ``cancel_job``, the function will never be
    executed.
    """
    store = waiting_threads  # reference for closing in `funcwrap`
    key = str(uuid.uuid4())
    # Uncover proxy objects in closure of `func`.
    newfunc = unproxy_closure(func)
    def funcwrap():
        newfunc()
        # Delete the reference to the thread in the apps global after running
        if key in store['cancelable_jobs']:
            del store['cancelable_jobs'][key]
    timer = threading.Timer(timeout, funcwrap)
    timer.start()
    store['cancelable_jobs'][key] = timer
    return key


def cancel_job(key):
    """Cancel a job launched with ``launch_cancelable_job``

    :param key: uuid returned by a previous call to ``launch_cancelable_job``
    """
    timer = waiting_threads['cancelable_jobs'].get(key)
    if timer:
        timer.cancel()
        del waiting_threads['cancelable_jobs'][key]
        return True
    return False


def launch_undoable_job(func, timeout):
    """Launch a thread with an undo function.  The function will be called
    only on request through a call to ``undo_job()``, otherwise, it will
    vanish.

    :param func: called if undo_job() is called for this job's key.
    :params timeout: timeout in seconds
    :rtype The UUID key of this job, used to reference further undo calls.
    """
    key = str(uuid.uuid4())
    store = waiting_threads  # reference for closing in `run`
    class Undoable(object):
        def __init__(self, func, timeout):
            self.trigger_queue = Queue()
            self.return_queue = Queue()
            self.func = func
            self.timeout = timeout
        def run(self):
            """Ran in separate thread, waiting for trigger_queue to fill"""
            # Block on the queue, if we get something, we run the function.
            try:
                if self.trigger_queue.get(block=True, timeout=self.timeout):
                    self.return_queue.put(self.func())
            except Empty, e:
                # Remove this object's reference from waiting_threads
                del store['undoable_jobs'][key]
        def undo(self):
            # Accessed from a new request's thread.
            # Block on put
            self.trigger_queue.put('STOP', block=True)
    newfunc = unproxy_closure(func)
    obj = Undoable(newfunc, timeout)
    thrd = threading.Thread(target=obj.run)
    thrd.start()
    store['undoable_jobs'][key] = obj
    return key


def undo_job(key, timeout=None):
    """Launch the ``undo`` function waiting in the thread associated with
    ``key``and wait for that function's return value for ``timeout`` seconds.

    If the other thread was timed out, the ``undo`` function will not be
    available to trigger anymore, and a ThreadLostError exception will be
    raised.
    """
    obj = waiting_threads['undoable_jobs'].get(key)
    if not obj:
        raise ThreadLostError("Thread doesn't exist. It either never existed, or you're too late")
    obj.undo()
    return obj.return_queue.get(block=True, timeout=timeout)

