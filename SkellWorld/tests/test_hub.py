#!/usr/bin/env python3
import importlib.util
import socket
import threading
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location("skellworld_hub",ROOT / "tools" / "skellworld_hub.py")
hub=importlib.util.module_from_spec(spec)
spec.loader.exec_module(hub)

class WorldHubTests(unittest.TestCase):
    def setUp(self):
        self.server=hub.WorldServer(("127.0.0.1",0))
        self.thread=threading.Thread(target=self.server.serve_forever,daemon=True)
        self.thread.start()
        self.clients=[]
    def tearDown(self):
        for sock,file in self.clients:
            file.close()
            sock.close()
        self.server.shutdown()
        self.server.server_close()
        self.thread.join(timeout=3)
    def peer(self,instance,product):
        sock=socket.create_connection(self.server.server_address,timeout=3)
        sock.settimeout(3)
        file=sock.makefile("rb")
        self.clients.append((sock,file))
        sock.sendall(hub.encode("HELLO",instance,product,product))
        self.assertEqual(hub.decode(file.readline(256))[0],"WELCOME")
        return sock,file
    def test_protocol_and_roundtrip(self):
        a,af=self.peer("one","skell.eq")
        b,bf=self.peer("two","skell.tune")
        self.assertEqual(hub.decode(bf.readline(256)),["PEER","one","skell.eq","online"])
        self.assertEqual(hub.decode(af.readline(256)),["PEER","two","skell.tune","online"])
        a.sendall(hub.encode("EVENT","one","theme","neon"))
        self.assertEqual(hub.decode(bf.readline(256)),["EVENT","one","theme","neon"])
        a.sendall(hub.encode("BYE","one","skell.eq","offline"))
        self.assertEqual(hub.decode(bf.readline(256)),["PEER","one","skell.eq","offline"])
    def test_reject_malformed(self):
        for raw in (b"SW2|HELLO|x|skell.eq|EQ\n",b"SW1|HELLO|x|skell.eq|has|pipe\n",
                    b"SW1|EVENT|x|theme|bad\ninjected\n",b"\xff\n",b"a"*512+b"\n"):
            self.assertIsNone(hub.decode(raw))
        self.assertIsNone(hub.decode(b"SW1|HELLO|x|skell.eq|\n"))
    def test_duplicate_instance_rejected(self):
        a,af=self.peer("same","skell.eq")
        dup=socket.create_connection(self.server.server_address,timeout=3)
        dup.settimeout(3)
        with dup.makefile("rb") as f:
            dup.sendall(hub.encode("HELLO","same","skell.eq","duplicate"))
            self.assertEqual(hub.decode(f.readline(256))[0],"ERROR")
        dup.close()
        b,bf=self.peer("other","skell.tune")
        self.assertEqual(hub.decode(bf.readline(256))[0],"PEER")
    def test_no_remote_commands(self):
        a,af=self.peer("one","skell.eq")
        b,bf=self.peer("two","skell.tune")
        bf.readline(256);af.readline(256)
        a.sendall(hub.encode("EVENT","one","plugin.setParameter","gain=9"))
        self.assertEqual(hub.decode(bf.readline(256)),["PEER","one","skell.eq","offline"])
    def test_parallel_joins_have_exact_peer_counts(self):
        from concurrent.futures import ThreadPoolExecutor
        start=threading.Barrier(6)
        def join(index):
            sock=socket.create_connection(self.server.server_address, timeout=4)
            sock.settimeout(4)
            stream=sock.makefile("rb")
            self.clients.append((sock,stream))
            start.wait(timeout=4)
            ident="instance-"+str(index)
            sock.sendall(hub.encode("HELLO",ident,"skell.demo","Demo"))
            welcome=hub.decode(stream.readline(256))
            peers=[hub.decode(stream.readline(256)) for _ in range(5)]
            return ident,welcome,peers
        with ThreadPoolExecutor(max_workers=6) as workers:
            rows=list(workers.map(join,range(6)))
        for ident,welcome,peers in rows:
            self.assertEqual(welcome,["WELCOME","hub","status","connected"])
            self.assertEqual(len(peers),5)
            self.assertTrue(all(p and p[0]=="PEER" and p[3]=="online" for p in peers))
            self.assertEqual({p[1] for p in peers},{r[0] for r in rows}-{ident})
        self.assertEqual(self.server.snapshot()["peer_count"],6)

    def test_parallel_events_are_complete_frames(self):
        from concurrent.futures import ThreadPoolExecutor
        a,af=self.peer("left","skell.left")
        b,bf=self.peer("right","skell.right")
        self.assertEqual(hub.decode(af.readline(256))[0],"PEER")
        self.assertEqual(hub.decode(bf.readline(256))[0],"PEER")
        c,cf=self.peer("watch","skell.watch")
        for _ in range(2):
            self.assertEqual(hub.decode(cf.readline(256))[0],"PEER")
        self.assertEqual(hub.decode(af.readline(256))[0],"PEER")
        self.assertEqual(hub.decode(bf.readline(256))[0],"PEER")
        def send(sock,identity):
            for n in range(12):
                sock.sendall(hub.encode("EVENT",identity,"theme",f"{identity}-{n}"))
        with ThreadPoolExecutor(max_workers=2) as workers:
            jobs=[workers.submit(send,a,"left"),workers.submit(send,b,"right")]
            messages=[hub.decode(cf.readline(256)) for _ in range(24)]
            for job in jobs: job.result(timeout=5)
        self.assertTrue(all(m and m[0]=="EVENT" and m[2]=="theme" for m in messages))
        self.assertEqual({m[3] for m in messages},
                         {f"{identity}-{n}" for identity in ("left","right") for n in range(12)})

    def test_loopback_only(self):
        self.assertEqual(self.server.server_address[0],"127.0.0.1")
        with self.assertRaises(ValueError):
            hub.WorldServer(("0.0.0.0",0))

if __name__=="__main__":unittest.main()
