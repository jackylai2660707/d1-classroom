import sys,pathlib,unittest
sys.path.insert(0,str(pathlib.Path(__file__).resolve().parents[1]/'bridge'))
from bridge import Controller,FakeSDK,Refused
class Tests(unittest.TestCase):
 def setUp(self):
  self.now=10; self.sdk=FakeSDK();self.c=Controller(self.sdk,{'mac':'02:12:34:56:78:90'},lambda:self.now);self.lease=self.c.handle('/connect',{'expected_mac':'02:12:34:56:78:90'})['lease']
 def call(self,path,**data):return self.c.handle(path,{'lease':self.lease,**data})
 def begin(self):self.call('/begin');self.call('/command',action='stand');self.now+=.1
 def test_identity(self):
  with self.assertRaises(Refused):self.c.handle('/connect',{'expected_mac':'02:00:00:00:00:01'})
 def test_occupancy(self):
  with self.assertRaises(Refused):self.c.handle('/connect',{'expected_mac':'02:12:34:56:78:90'})
 def test_deadline(self):
  self.begin();self.call('/command',action='forward',args={'seconds':1,'speed':.15});self.now+=1.05;self.call('/heartbeat');self.c.tick();self.assertEqual(self.sdk.moves[-1],(0,0,0))
 def test_lost_heartbeat(self):
  self.begin();self.call('/command',action='forward',args={'seconds':3});self.now+=1.3;self.c.tick();self.assertEqual(self.sdk.moves[-1],(0,0,0));self.assertIsNone(self.c.lease)
 def test_reject_stale(self):
  self.begin();self.now+=1.3
  with self.assertRaises(Refused):self.call('/command',action='forward',args={'seconds':1})
 def test_low_battery(self):
  self.sdk.power=29
  with self.assertRaises(Refused):self.call('/begin')
 def test_limits(self):
  self.begin()
  for args in [{'seconds':4},{'seconds':1,'speed':.9},{'seconds':float('nan')},{'seconds':True}]:
   with self.assertRaises(Refused):self.call('/command',action='forward',args=args)
 def test_stop_cancels(self):
  self.begin();self.call('/stop')
  with self.assertRaises(Refused):self.call('/command',action='forward',args={'seconds':1})
 def test_job_limit(self):
  self.begin();self.now+=60.1;self.c.beat=self.now;self.c.tick();self.assertEqual(self.c.job_end,0)
 def test_old_lease_cannot_affect_new_owner(self):
  old=self.lease;self.call('/release');self.lease=self.c.handle('/connect',{'expected_mac':'02:12:34:56:78:90'})['lease']
  with self.assertRaises(Refused): self.c.handle('/stop',{'lease':old})
  self.assertEqual(self.c.lease,self.lease)
 def test_bad_battery_does_not_leave_ghost_owner(self):
  self.call('/release');self.sdk.power=float('nan')
  with self.assertRaises(Refused): self.c.handle('/connect',{'expected_mac':'02:12:34:56:78:90'})
  self.assertIsNone(self.c.lease)
 def test_concurrent_connect_only_one_owner(self):
  from concurrent.futures import ThreadPoolExecutor
  self.call('/release')
  def connect(_):
   try: self.c.handle('/connect',{'expected_mac':'02:12:34:56:78:90'});return True
   except Refused: return False
  with ThreadPoolExecutor(8) as pool: self.assertEqual(sum(pool.map(connect,range(8))),1)
 def test_discovery_has_no_side_effects(self):
  from bridge import discovery_reply
  import json
  self.c.ready=True;beat=self.c.beat
  response=discovery_reply(self.c,json.dumps({'type':'d1-discover-v1','request':'a'*32}).encode())
  self.assertEqual(response['state'],'busy');self.assertNotIn('lease',response);self.assertEqual(self.c.beat,beat);self.assertEqual(self.sdk.moves,[])
  self.assertIsNone(discovery_reply(self.c,b'[]'))
  self.assertIsNone(discovery_reply(self.c,b'{"type":"d1-discover-v1","request":"wrong"}'))
if __name__=='__main__':unittest.main()
