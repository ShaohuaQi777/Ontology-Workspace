"""Single-process owned native consumer. File ownership is not a distributed lease."""
import fcntl,os,stat,threading
from .worker import NativeJobWorker


class LocalWorkerRuntime:
    def __init__(self,jobs,worker_id='local-worker'):
        jobs._key(worker_id)
        self.jobs=jobs; self.worker_id=worker_id
        self._fd=None; self._thread=None; self._stop=threading.Event(); self.healthy=False

    def start(self):
        if self._fd is not None: raise RuntimeError('SERVICE_ALREADY_RUNNING')
        database=self.jobs.store.database_path
        database_info=database.lstat()
        if database_info.st_nlink!=1: raise RuntimeError('SERVICE_STORAGE_INVALID')
        lock_path=database.with_name(database.name+'.worker.lock')
        fd=os.open(lock_path,os.O_RDWR|os.O_CREAT|os.O_NOFOLLOW|os.O_CLOEXEC,0o600)
        try:
            info=os.fstat(fd)
            if not stat.S_ISREG(info.st_mode) or info.st_uid!=os.geteuid() or stat.S_IMODE(info.st_mode)&0o077: raise RuntimeError('SERVICE_STORAGE_INVALID')
            try: fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
            except BlockingIOError: raise RuntimeError('SERVICE_ALREADY_RUNNING') from None
            current=lock_path.lstat()
            if (current.st_dev,current.st_ino)!=(info.st_dev,info.st_ino): raise RuntimeError('SERVICE_STORAGE_INVALID')
            # Exclusive ownership proves no previous configured server still owns this DB.
            self.jobs.recover_interrupted(self.worker_id)
            self._fd=fd; self._stop.clear(); self.healthy=True
            self._thread=threading.Thread(target=self._consume,name='ontology-local-worker',daemon=True)
            self._thread.start()
        except BaseException:
            os.close(fd); self._fd=None; self.healthy=False; raise

    def _consume(self):
        worker=NativeJobWorker(self.jobs)
        try:
            while not self._stop.is_set():
                if not worker.run_one(self.worker_id): self._stop.wait(.2)
        except Exception:
            self.healthy=False; self._stop.set()

    def stop(self):
        self._stop.set()
        if self._thread is not None:
            self._thread.join(timeout=100)
            if self._thread.is_alive(): raise RuntimeError('SERVICE_STOP_PENDING')
        self.healthy=False
        if self._fd is not None:
            os.close(self._fd); self._fd=None
