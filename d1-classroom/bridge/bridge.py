"""D1 classroom bridge. Python 3.10, standard library only. Never runs student code."""
import argparse, json, math, secrets, threading, time, socket, pathlib, re, signal, sys, ipaddress
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from highlevel import EXTRA_ACTIONS, SENSORS, command as extra_command, stop_extra, tick_extra

class Refused(Exception): pass

class Controller:
    refused=Refused
    def __init__(self, sdk, identity, clock=time.monotonic):
        self.sdk=sdk; self.identity=identity; self.clock=clock
        self.lock=threading.RLock(); self.lease_lock=threading.RLock(); self.lease=None; self.client=None
        self.beat=0; self.job_end=0; self.motion_end=0; self.v=(0,0,0)
        self.state='idle'; self.posture='unknown'; self.error=None; self.ready=False; self.cached_battery=None
        self.allow_high_risk=False; self.allow_backflip=False; self.extra_kind=None; self.extra_action=None; self.extra_velocity=(); self.sensor_cache={}
    def call_sdk(self, method, *args):
        function=getattr(self.sdk,method,None)
        if not callable(function): raise Refused('機身 SDK 不支援：'+method)
        result=function(*args)
        if result is None and (method=='cancelTwoLegStand' or isinstance(self.sdk,FakeSDK)): return
        if type(result) is not int or result!=0:
            code=hex(result) if type(result) is int else repr(result)
            raise Refused('SDK 拒絕 '+method+'，回傳碼 '+code+'；不能視為動作完成')
    def zero_velocity(self):
        reader=getattr(self.sdk,'getCurrentCtrlmode',None)
        try: mode=reader() if callable(reader) else None
        except Exception: mode=None
        if type(mode) is int and mode in (0,10,51): return
        self.call_sdk('move',0,0,0)
    def stop(self):
        self.v=(0,0,0); self.job_end=0; self.allow_high_risk=False; self.allow_backflip=False
        handled=stop_extra(self)
        if handled=='uninterruptible':
            self.state='stop_unconfirmed'
            return {'stop':'not_confirmed','physical_stop':'observe','warning':'特技已開始，SDK 沒有中止介面；請按現場硬體停止方案處理'}
        self.motion_end=0
        if not handled: self.zero_velocity()
        self.state='stop_command_accepted'
        return {'stop':'command_accepted','physical_stop':'observe'}
    def check(self, lease):
        with self.lease_lock:
            if not self.lease or not secrets.compare_digest(str(lease),self.lease): raise Refused('控制權無效或已過期，請重新連接')
            expired=self.clock()-self.beat>1.2
            if expired: self.lease=None
        if expired:
            self.stop()
            raise Refused('心跳已過期，停止指令已送出')
    def heartbeat(self, data):
        # Never queue a heartbeat behind SDK I/O or call the native SDK here.
        # Invalid/late packets cannot revive a lease; the watchdog handles stopping.
        with self.lease_lock:
            if not self.lease or not secrets.compare_digest(str(data.get('lease')),self.lease): raise Refused('控制權無效或已過期，請重新連接')
            now=self.clock()
            if now-self.beat>1.2: raise Refused('心跳已過期，請重新連接並確認機器狗停止')
            self.beat=now
            return {'battery':self.cached_battery,'state':self.state}
    def battery(self):
        b=float(self.sdk.getBatteryPower())
        if not math.isfinite(b) or not 0<=b<=100: raise Refused('無法讀取有效電量')
        self.cached_battery=round(b)
        return self.cached_battery
    def refresh(self):
        with self.lock:
            self.ready=bool(self.sdk.checkConnect())
            battery=self.battery()
            if self.job_end and (battery<30 or not self.ready): self.stop()
    def connect(self, data):
        if normalize_mac(data.get('expected_mac'))!=self.identity['mac']: raise Refused('機身 MAC 不一致，請重新掃描')
        with self.lease_lock:
            if self.lease and self.clock()-self.beat<=1.2: raise Refused('此機器狗正由另一台電腦使用')
            stale=bool(self.lease); self.lease=None
        if stale: self.stop()
        if self.error or not self.sdk.checkConnect(): raise Refused('SDK 未就緒，請通知老師')
        battery=self.battery()
        with self.lease_lock:
            self.lease=secrets.token_urlsafe(32); self.client=data.get('client'); self.beat=self.clock()
        return {**self.identity,'lease':self.lease,'battery':battery,'api_version':3}
    def handle(self, route, data):
        if not isinstance(data,dict): raise Refused('請求格式無效')
        if route=='/heartbeat': return self.heartbeat(data)
        with self.lock:
            if route=='/connect': return self.connect(data)
            self.check(data.get('lease'))
            if route in ['/stop','/end','/release']:
                try: return self.stop()
                finally:
                    if route=='/release':
                        with self.lease_lock: self.lease=None
            if route=='/begin':
                if self.job_end: raise Refused('已有程序運行，請先停止')
                if self.motion_end>self.clock(): raise Refused('特技尚未結束，不能啟動新程序')
                if self.battery()<30: raise Refused('電量低於 30%，請充電後再測試')
                if not self.sdk.checkConnect(): raise Refused('SDK 連接中斷')
                self.allow_high_risk=data.get('allow_high_risk') is True
                self.allow_backflip=self.allow_high_risk and data.get('allow_backflip') is True
                self.job_end=self.clock()+60; self.state='running'; return {'accepted':True}
            if route!='/command': raise Refused('不支援此路徑')
            a=data.get('action'); args=data.get('args') or {}
            if not isinstance(args,dict): raise Refused('指令參數格式無效')
            if a=='stop':
                end=self.job_end; flags=(self.allow_high_risk,self.allow_backflip); r=self.stop(); self.job_end=end
                if r['stop']=='command_accepted': self.allow_high_risk,self.allow_backflip=flags
                return r
            if not self.job_end or self.clock()>=self.job_end: self.stop(); raise Refused('程序已取消或超過 60 秒')
            if self.battery()<30 or not self.sdk.checkConnect(): self.stop(); raise Refused('電量或 SDK 連接異常，程序取消')
            if a=='battery': return {'value':self.battery()}
            result=extra_command(self,a,args)
            if result is not None: return result
            def num(name,lo,hi,default=None):
                x=args.get(name,default)
                if isinstance(x,bool) or not isinstance(x,(int,float)) or not math.isfinite(x) or not lo<=x<=hi: raise Refused(f'{name} 超出課程限制')
                return x
            if a=='wait': return {'duration_ms':num('seconds',0,5)*1000}
            if self.motion_end>self.clock(): raise Refused('上個動作尚未完成')
            if a in ['stand','lie']:
                self.zero_velocity(); self.v=(0,0,0)
                if a=='stand': self.call_sdk('standUp'); self.posture='stand'
                else: self.call_sdk('lieDown'); self.posture='lie'
                return {'duration_ms':2000}
            if self.posture!='stand': raise Refused('請先執行站立')
            if a in ['forward','back']:
                seconds=num('seconds',.1,3); speed=num('speed',.05,.2,.15)
                self.v=(speed if a=='forward' else -speed,0,0)
            elif a in ['left','right']:
                degrees=num('degrees',1,45); seconds=degrees*math.pi/180/.3
                self.v=(0,0,.3 if a=='left' else -.3)
            else: raise Refused('不支援此動作')
            self.call_sdk('move',*self.v); self.motion_end=min(self.clock()+seconds,self.job_end)
            return {'duration_ms':seconds*1000+100,'note':'轉角由時間估算，需實測'}
    def tick(self):
        with self.lock:
            now=self.clock()
            with self.lease_lock:
                expired=bool(self.lease) and now-self.beat>1.2
                if expired: self.lease=None
            if expired:
                self.stop()
                return
            if self.job_end and now>=self.job_end: self.stop(); return
            if tick_extra(self,now): return
            if self.motion_end:
                if now>=self.motion_end:
                    self.v=(0,0,0); self.motion_end=0; self.call_sdk('move',0,0,0)
                else: self.call_sdk('move',*self.v)

class FakeSDK:
    """Explicit software test backend. It cannot move a real robot."""
    def __init__(self): self.moves=[]; self.power=80; self.mode=0; self.calls=[]
    def initRobot(self,*a): pass
    def move(self,*a): self.moves.append(a); return 0
    def standUp(self): self.mode=1; return 0
    def lieDown(self): self.mode=51; return 0
    def passive(self): self.calls.append(('passive',)); self.mode=0; return 0
    def shakeHand(self): self.calls.append(('shakeHand',)); return 0
    def jump(self): self.calls.append(('jump',)); self.mode=21; return 0
    def frontJump(self): self.calls.append(('frontJump',)); self.mode=21; return 0
    def backflip(self): self.calls.append(('backflip',)); self.mode=21; return 0
    def twoLegStand(self,*a): self.calls.append(('twoLegStand',*a)); self.mode=21; return 0
    def cancelTwoLegStand(self): self.calls.append(('cancelTwoLegStand',)); self.mode=1
    def attitudeControl(self,*a): self.calls.append(('attitudeControl',*a)); self.mode=21; return 0
    def getCurrentCtrlmode(self): return self.mode
    def __getattr__(self,name):
        if name=='getQuaternion': return lambda: [1,0,0,0]
        if name in {m for methods in SENSORS.values() for m in methods}:
            return lambda: [0]*(4 if name.startswith('getLeg') else 3)
        raise AttributeError(name)
    def checkConnect(self): return True
    def getBatteryPower(self): return self.power

def normalize_mac(value):
    if not isinstance(value,str): return None
    value=value.replace('-',':').upper()
    if not re.fullmatch(r'(?:[0-9A-F]{2}:){5}[0-9A-F]{2}',value): return None
    if value=='00:00:00:00:00:00' or int(value[:2],16)&1: return None
    return value


def read_mac(interface, root=pathlib.Path('/sys/class/net')):
    if not re.fullmatch(r'[A-Za-z0-9_.-]{1,32}',interface or ''): raise ValueError('網卡名稱無效')
    mac=normalize_mac((root/interface/'address').read_text().strip())
    if not mac: raise ValueError('無法讀取有效 MAC')
    return mac


def interface_ip(interface):
    import fcntl,struct
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        return socket.inet_ntoa(fcntl.ioctl(sock.fileno(),0x8915,struct.pack('256s',interface.encode()[:15]))[20:24])


def interface_network(interface):
    import fcntl,struct
    with socket.socket(socket.AF_INET,socket.SOCK_DGRAM) as sock:
        mask=socket.inet_ntoa(fcntl.ioctl(sock.fileno(),0x891b,struct.pack('256s',interface.encode()[:15]))[20:24])
    return ipaddress.IPv4Network((interface_ip(interface),mask),strict=False)


def discovery_networks(interface, root=pathlib.Path('/sys/class/net')):
    """Read current Wi-Fi subnets; AP discovery never changes the identity MAC."""
    networks=[]
    for name in dict.fromkeys((interface, 'ap0')):
        path=root/name
        try:
            if not ((path/'wireless').exists() or (path/'phy80211').exists()): continue
            if not int((path/'flags').read_text().strip(), 16) & 1: continue  # IFF_UP
            network=interface_network(name)
            # An unconfigured/invalid interface must not admit every IPv4 source.
            if not network.prefixlen or network.network_address.is_unspecified: continue
            networks.append(network)
        except (OSError, ValueError):
            # AP mode may be enabling/disabling while a discovery packet arrives.
            continue
    return networks


def discovery_source_allowed(interface, address, root=pathlib.Path('/sys/class/net')):
    peer=ipaddress.IPv4Address(address)
    return any(peer in network for network in discovery_networks(interface, root))


def discovery_reply(controller, packet):
    if len(packet)>512: return None
    try:
        data=json.loads(packet)
        nonce=data.get('request')
        if data.get('type')!='d1-discover-v1' or not isinstance(nonce,str) or not re.fullmatch(r'[0-9a-f]{32}',nonce): return None
    except (ValueError,AttributeError,TypeError): return None
    with controller.lock:
        state='unavailable' if not controller.ready or controller.error else 'busy' if controller.lease else 'available'
        return {'type':'d1-robot-v1','request':nonce,'mac':controller.identity['mac'],'state':state}


def make_server(controller, address):
    class Handler(BaseHTTPRequestHandler):
        protocol_version='HTTP/1.1'
        def log_message(self,*args): pass
        def setup(self):
            super().setup(); self.connection.settimeout(2)
        def reply(self,code,result):
            body=json.dumps(result,ensure_ascii=False).encode()
            self.send_response(code);self.send_header('Content-Type','application/json; charset=utf-8')
            self.send_header('Content-Length',str(len(body)))
            if self.close_connection: self.send_header('Connection','close')
            self.end_headers();self.wfile.write(body)
        def do_GET(self):
            if self.path!='/status': self.reply(404,{'error':'不存在的路徑'});return
            with controller.lock:
                self.reply(200,{'mac':controller.identity['mac'],'sdk_ready':controller.ready and not bool(controller.error)})
        def do_POST(self):
            # Parsing failures cannot stop somebody else's active program.
            try:
                n=int(self.headers.get('Content-Length','0'))
                if not 0<n<4096: raise ValueError('請求大小無效')
                data=json.loads(self.rfile.read(n))
                if not isinstance(data,dict): raise ValueError('請求格式無效')
            except (ValueError,TypeError,socket.timeout):
                # Do not reuse a connection whose request body may be unread.
                self.close_connection=True
                self.reply(400,{'error':'請求格式無效'});return
            try:
                result=controller.handle(self.path,data);code=200
            except Refused as error:
                result={'error':str(error)};code=409
            except Exception as error:
                controller.error=str(error)
                try: controller.stop()
                except Exception: pass
                result={'error':'SDK 錯誤，已嘗試停止，請通知老師'};code=503
                print(type(error).__name__,str(error),flush=True)
            self.reply(code,result)
    return ThreadingHTTPServer(address,Handler)


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--config',required=True);parser.add_argument('--fake',action='store_true')
    args=parser.parse_args()
    config=json.loads(pathlib.Path(args.config).read_text(encoding='utf-8-sig'))
    mac=normalize_mac(config.get('mac')) if args.fake else read_mac(config['interface'])
    if not mac: raise SystemExit('測試配置缺少有效 MAC')
    address=config.get('bind','0.0.0.0');port=int(config.get('port',8765))
    if args.fake:
        sdk=FakeSDK();print('SOFTWARE TEST MODE. No physical SDK.',flush=True)
    else:
        import mc_sdk_zsl_1_py
        sdk=mc_sdk_zsl_1_py.HighLevel()
        local=config.get('sdk_local_ip','127.0.0.1');robot=config.get('sdk_robot_ip','127.0.0.1')
        if local=='auto': local=interface_ip(config['interface'])
        if robot=='auto': robot=interface_ip(config['interface'])
        sdk.initRobot(local,43988,robot)
    controller=Controller(sdk,{'mac':mac})
    udp=socket.socket(socket.AF_INET,socket.SOCK_DGRAM)
    udp.bind((address,port));udp.settimeout(.25)
    server=make_server(controller,(address,port))
    ended=threading.Event();fatal=[]
    def shutdown(*_):
        if not ended.is_set():
            ended.set();threading.Thread(target=server.shutdown,daemon=True).start()
    def watch():
        next_health=0
        while not ended.is_set():
            try:
                controller.tick()
                if time.monotonic()>=next_health:
                    controller.refresh()
                    next_health=time.monotonic()+.5
                    if not args.fake and read_mac(config['interface'])!=mac:
                        fatal.append('Wi-Fi MAC 已變更，停止並重新讀取身分');shutdown()
                    if not args.fake and (config.get('sdk_local_ip')=='auto' or config.get('sdk_robot_ip')=='auto'):
                        current=interface_ip(config['interface'])
                        if (config.get('sdk_local_ip')=='auto' and current!=local) or (config.get('sdk_robot_ip')=='auto' and current!=robot):
                            fatal.append('網路地址已變更，停止並重新初始化 SDK');shutdown()
            except Exception as error:
                controller.error=str(error);controller.ready=False
                try: controller.stop()
                except Exception: pass
            ended.wait(.05)
    def discover():
        while not ended.is_set():
            try:
                packet,peer=udp.recvfrom(1024)
                # Accept station Wi-Fi and vendor AP subnets, never Ethernet/VPN by default.
                allowed=(ipaddress.IPv4Address(peer[0]) in ipaddress.IPv4Network(config.get('test_network','0.0.0.0/0'))) if args.fake else discovery_source_allowed(config['interface'],peer[0])
                if not allowed: continue
                response=discovery_reply(controller,packet)
                if response: udp.sendto(json.dumps(response).encode(),peer)
            except socket.timeout: pass
            except ValueError: pass
            except OSError:
                if not ended.is_set(): fatal.append('UDP 掃描服務中斷');shutdown()
    threading.Thread(target=watch,daemon=True).start()
    threading.Thread(target=discover,daemon=True).start()
    signal.signal(signal.SIGTERM,shutdown);signal.signal(signal.SIGINT,shutdown)
    print(f'Bridge {mac} HTTP+UDP on {address}:{port}',flush=True)
    try: server.serve_forever(poll_interval=.1)
    finally:
        ended.set();udp.close();server.server_close()
        try: controller.stop()
        except Exception as error: print('Shutdown stop unconfirmed:',error,flush=True)
    if fatal: raise SystemExit('; '.join(fatal))

if __name__=='__main__': main()
