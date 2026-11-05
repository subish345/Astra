"""Observe real Mission Console + Ground Monitor. No frame or decision generation."""
import os, sys, time, json, dataclasses
from pathlib import Path
from collections import Counter, defaultdict
import numpy as np, cv2, psutil
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QTimer
run=Path(__file__).resolve().parent
sys.path.insert(0,str(run/'workspace'))
from core.ui.main_window import MissionConsoleWindow
from core.camera.webcam import WebcamSource
from apps.ground_monitor.app import GroundMonitorWindow

samples=[]; stages=defaultdict(list); event_counts=Counter(); observations=Counter(); frames=0; captures=0; failed_reads=0; raw_writer=None; latest=None
raw_log=(run/'camera/frame_timestamps.jsonl').open('w'); events=(run/'mission_console/live_events.jsonl').open('w')
source_read=WebcamSource.read

def measured_read(source):
 global captures, failed_reads, raw_writer
 t=time.perf_counter(); fd=source_read(source); stages['capture_ms'].append((time.perf_counter()-t)*1000)
 if fd is None:failed_reads+=1;return fd
 captures+=1
 if raw_writer is None:
  raw_writer=cv2.VideoWriter(str(run/'camera/real_camera_observation.avi'),cv2.VideoWriter_fourcc(*'MJPG'),source.get_fps(),(fd.width,fd.height))
  if not raw_writer.isOpened():raise RuntimeError('QA evidence video writer failed')
 raw_writer.write(fd.image)
 raw_log.write(json.dumps({'capture':captures,'frame_id':fd.frame_id,'mono':fd.timestamp_mono,'wall':fd.timestamp_wall.isoformat(),'source':fd.source_id})+'\n')
 if captures in [1,900,1800]:cv2.imwrite(str(run/'camera'/f'clean_{captures}.jpg'),fd.image)
 return fd
WebcamSource.read=measured_read
app=QApplication.instance() or QApplication([]); app.setQuitOnLastWindowClosed(False)
window=MissionConsoleWindow(session_id=run.name+'-LIVE1'); ground=None
start=time.monotonic(); process=psutil.Process(); process.cpu_percent(); window.show()

def event(kind,payload):
 event_counts[kind]+=1
 events.write(json.dumps({'elapsed':time.monotonic()-start,'type':kind,'payload':payload},default=str)+'\n');events.flush()

def on_frame(frame,state):
 global frames,latest
 frames+=1; latest=state
 for key,val in dataclasses.asdict(state.latency).items(): stages[key].append(val)
 observations['frames_with_pose']+=bool(state.poses);observations['frames_with_hands']+=bool(state.hands)
 for pose in state.poses:observations['landmark_count_'+str(len(pose.keypoints))]+=1
 for obj in state.objects:observations['object_'+obj.class_name]+=1
 if frames in [1,600,1800]:
  cv2.imwrite(str(run/'perception'/f'overlay_{frames}.jpg'),frame)
  (run/'perception'/f'state_{frames}.json').write_text(json.dumps(dataclasses.asdict(state),default=str,indent=2))

window.bridge.sig_frame_ready.connect(on_frame)
window.bridge.sig_session_status.connect(lambda s:event('session',s))
window.bridge.sig_timeline_event.connect(lambda *a:event('timeline',a))
window.bridge.sig_assurance_decision.connect(lambda d,s:event('assurance',d.to_dict()))
window.bridge.sig_evidence_bundle.connect(lambda b:event('evidence',b.to_dict()) if frames%30==0 else None)
window.bridge.sig_step_progress.connect(lambda s:event('procedure',dataclasses.asdict(s)) if frames%30==0 else None)
window.bridge.sig_health.connect(lambda s:event('health',s))
window.bridge.sig_voice.connect(lambda *a:event('voice',a))
window.start_mission()

def start_ground():
 global ground
 ground=GroundMonitorWindow();ground.show()
 ground.state.sig_link_changed.connect(lambda s:event('ground_link',s))

def sample():
 samples.append({'elapsed':time.monotonic()-start,'frames':frames,'rss_mb':process.memory_info().rss/1048576,'cpu_percent':process.cpu_percent()})

sample_timer=QTimer();sample_timer.timeout.connect(sample);sample_timer.start(1000)

def capture_ui(label):
 window.stack.setCurrentIndex(0); window.grab().save(str(run/'mission_console'/f'{label}.png'))
 if ground:ground.grab().save(str(run/'streaming'/f'{label}.png'))
 event('ui_capture',label)

def restart():
 if window.worker and window.worker.isRunning():event('restart_blocked','Previous worker still running');return
 window.session_id=run.name+'-LIVE2';window.start_mission();event('restart','requested')

def finish():
 sample_timer.stop();capture_ui('final');window.stop_mission()
 if window.worker and window.worker.isRunning():QTimer.singleShot(1000,finish);return
 if ground:ground.close()
 window.close()
 if raw_writer:raw_writer.release()
 raw_log.close();events.close()
 metrics={'duration_seconds':time.monotonic()-start,'frames':frames,'captures':captures,'read_failures':failed_reads,'delivered_fps_including_ui_actions':frames/(time.monotonic()-start),'observations':dict(observations),'events':dict(event_counts),'samples':samples,'stage_latency_ms':{k:{'p50':float(np.percentile(v,50)),'p95':float(np.percentile(v,95)),'p99':float(np.percentile(v,99))} for k,v in stages.items() if v},'recording_scope':'QA observer of real camera; not proof of built-in Mission Console recording','human_acceptance':'PENDING; no physical action labels asserted'}
 (run/'performance/live_console_metrics.json').write_text(json.dumps(metrics,indent=2));print(json.dumps({k:v for k,v in metrics.items() if k!='samples'},indent=2));app.quit()

QTimer.singleShot(5000,start_ground)
QTimer.singleShot(15000,lambda:capture_ui('running'))
QTimer.singleShot(20000,lambda:window.resize(1300,800))
QTimer.singleShot(22000,lambda:window.stack.setCurrentIndex(1))
QTimer.singleShot(25000,lambda:window.stack.setCurrentIndex(0))
QTimer.singleShot(30000,lambda:window.console_view.video_panel.btn_pose.setChecked(False))
QTimer.singleShot(32000,lambda:capture_ui('pose_off'))
QTimer.singleShot(35000,lambda:window.console_view.video_panel.btn_pose.setChecked(True))
QTimer.singleShot(45000,lambda:(event('ground_disconnect','controlled client disconnection'),ground.conn_mgr.disconnect_all()))
QTimer.singleShot(53000,lambda:capture_ui('ground_disconnected'))
QTimer.singleShot(60000,lambda:(event('ground_reconnect','controlled client reconnection'),ground.conn_mgr.connect_all()))
QTimer.singleShot(70000,lambda:capture_ui('reconnected'))
QTimer.singleShot(85000,lambda:(event('stop','requested'),window.stop_mission()))
QTimer.singleShot(90000,restart)
QTimer.singleShot(120000,finish)
app.exec()
