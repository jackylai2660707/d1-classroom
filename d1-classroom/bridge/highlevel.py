"""Bounded zsl-1 high-level commands. Never exposes per-motor control."""
import math

SENSORS = {
    'mode': ('getCurrentCtrlmode',), 'quaternion': ('getQuaternion',),
    'rpy': ('getRPY',), 'acceleration': ('getBodyAcc',), 'gyro': ('getBodyGyro',),
    'position': ('getPosition',), 'world_velocity': ('getWorldVelocity',),
    'body_velocity': ('getBodyVelocity',),
    'joints_position': ('getLegAbadJoint', 'getLegHipJoint', 'getLegKneeJoint'),
    'joints_velocity': ('getLegAbadJointVel', 'getLegHipJointVel', 'getLegKneeJointVel'),
    'joints_torque': ('getLegAbadJointTorque', 'getLegHipJointTorque', 'getLegKneeJointTorque'),
}
HIGH_RISK = frozenset(('jump', 'front_jump', 'backflip', 'two_leg_stand'))
EXTRA_ACTIONS = frozenset(('greet', 'passive', 'side_left', 'side_right', 'move', 'attitude', 'cancel_two_leg_stand', 'telemetry')) | HIGH_RISK


def number(args, name, low, high, default):
    value = args.get(name, default)
    if isinstance(value, bool) or not isinstance(value, (int, float)) or not math.isfinite(value) or not low <= value <= high:
        raise ValueError(name + ' 超出課程限制')
    return value


def telemetry(c, name):
    methods = SENSORS.get(name) if isinstance(name,str) else None
    if not methods:
        raise c.refused('不支援的感測資料')
    old = c.sensor_cache.get(name)
    if old and c.clock() - old[0] < .05:
        return old[1]
    values = []
    for method in methods:
        reader = getattr(c.sdk, method, None)
        if not callable(reader):
            raise c.refused('機身 SDK 不支援：' + method)
        value = reader()
        if name == 'mode':
            if isinstance(value, bool) or not isinstance(value, int) or not 0 <= value <= 65535:
                raise c.refused('SDK 回傳的控制模式無效')
        else:
            value = list(value)
            size = 4 if name == 'quaternion' or name.startswith('joints_') else 3
            if len(value) != size or any(isinstance(v, bool) or not isinstance(v, (int, float)) or not math.isfinite(v) for v in value):
                raise c.refused('SDK 回傳的感測資料無效：' + name)
        values.append(value)
    result = dict(zip(('abad', 'hip', 'knee'), values)) if name.startswith('joints_') else values[0]
    c.sensor_cache[name] = (c.clock(), result)
    return result


def stop_extra(c):
    if c.extra_kind == 'two_leg':
        c.call_sdk('cancelTwoLegStand')
        c.posture = 'unknown'
    elif c.extra_kind == 'attitude':
        c.call_sdk('attitudeControl', 0, 0, 0, 0)
        c.posture = 'unknown'
    elif c.extra_kind == 'special' and c.clock() < c.motion_end:
        # The vendor API exposes no cancellation primitive for jumps/flips.
        return 'uninterruptible'
    else:
        return False
    c.extra_kind = None
    return True


def tick_extra(c, now):
    if not c.extra_kind:
        return False
    if now >= c.motion_end:
        if c.extra_kind == 'special':
            c.extra_kind = None
            c.posture = 'stand' if c.extra_action == 'greet' else 'unknown'
        else:
            stop_extra(c)
        c.motion_end = 0
        return True
    if c.extra_kind == 'attitude':
        c.call_sdk('attitudeControl', *c.extra_velocity)
    elif c.extra_kind == 'two_leg':
        c.call_sdk('twoLegStand', 0, 0)
    return True


def command(c, action, args):
    if action not in EXTRA_ACTIONS:
        return None
    if action == 'telemetry':
        return {'value': telemetry(c, args.get('name'))}
    if action in HIGH_RISK and not c.allow_high_risk:
        raise c.refused('高風險動作未啟用；先閱讀風險並允許本次程序')
    if action == 'backflip' and not c.allow_backflip:
        raise c.refused('後空翻是危險指令，須另外明確允許本次後空翻')
    if action == 'cancel_two_leg_stand':
        if c.extra_kind != 'two_leg':
            return {'duration_ms': 0}
        stop_extra(c)
        c.motion_end = 0
        return {'duration_ms': 500}
    if c.motion_end > c.clock():
        raise c.refused('上個動作尚未完成，不能切換姿態')
    if action == 'passive':
        c.call_sdk('passive')
        c.posture = 'passive'
        return {'duration_ms': 2000}
    if c.posture != 'stand':
        raise c.refused('請先執行站立；姿態調整或特技後也須重新站立')
    try:
        if action in ('side_left', 'side_right', 'move'):
            seconds = number(args, 'seconds', .1, 3, 1)
            if action == 'move':
                vx = number(args, 'vx', -.2, .2, 0)
                vy = number(args, 'vy', -.2, .2, 0)
                yaw = number(args, 'yaw_rate', -.3, .3, 0)
                if math.hypot(vx, vy) > .200000001 or any(v != 0 and abs(v) < m for v, m in ((vx, .05), (vy, .1), (yaw, .02))):
                    raise ValueError('移動速度不符合 SDK／課程限制')
            else:
                speed = number(args, 'speed', .1, .2, .1)
                vx, vy, yaw = 0, speed if action == 'side_left' else -speed, 0
            c.call_sdk('move', vx, vy, yaw)
            c.v = (vx, vy, yaw)
        elif action == 'attitude':
            seconds = number(args, 'seconds', .1, 1, .5)
            velocity = tuple(number(args, name, -limit, limit, 0) for name, limit in (('roll', .1), ('pitch', .1), ('yaw', .1), ('height', .02)))
            c.call_sdk('attitudeControl', *velocity)
            c.extra_velocity = velocity
            c.extra_kind = 'attitude'
        elif action == 'two_leg_stand':
            seconds = number(args, 'seconds', .1, 2, 1)
            if not callable(getattr(c.sdk,'cancelTwoLegStand',None)):
                raise c.refused('SDK 缺少退出雙腿站立介面，拒絕開始此動作')
            c.call_sdk('twoLegStand', 0, 0)
            c.posture = 'two_leg'
            c.extra_kind = 'two_leg'
        else:
            method, seconds = {'greet': ('shakeHand', 4), 'jump': ('jump', 4), 'front_jump': ('frontJump', 4), 'backflip': ('backflip', 5)}[action]
            if c.clock()+seconds+.2>c.job_end:
                raise c.refused('程序剩餘時間不足，不能開始此動作')
            c.call_sdk(method)
            c.extra_kind = 'special'
            c.extra_action = action
            c.posture = 'unknown'
        c.motion_end = min(c.clock() + seconds, c.job_end)
        return {'duration_ms': seconds * 1000 + 100}
    except ValueError as error:
        raise c.refused(str(error))
