/**
 * WebRTC setup: media capture, peer connection, and audio streaming.
 */

const ICE_SERVERS = [{
  urls: 'stun:stun.l.google.com:19302'
}];
export async function createConnection(onStateChange, onMessage) {
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
      sampleRate: 48000
    },
    video: false
  });
  const pc = new RTCPeerConnection({
    iceServers: ICE_SERVERS
  });
  const dc = pc.createDataChannel('transcript', {
    ordered: true
  });
  dc.onmessage = event => {
    onMessage?.(event.data);
  };
  dc.onopen = () => console.log("DataChannel ('transcript') opened");
  dc.onclose = () => console.log("DataChannel ('transcript') closed");
  pc.onconnectionstatechange = () => {
    onStateChange?.(pc.connectionState);
  };
  stream.getAudioTracks().forEach(track => pc.addTrack(track, stream));
  const offer = await pc.createOffer();
  await pc.setLocalDescription(offer);
  await waitForIce(pc, 3000);
  return {
    pc,
    stream,
    offer: {
      sdp: pc.localDescription.sdp,
      type: pc.localDescription.type
    }
  };
}
export async function applyAnswer(pc, answer) {
  await pc.setRemoteDescription(new RTCSessionDescription(answer));
}
export function closeConnection(pc, stream) {
  if (pc) {
    pc.onconnectionstatechange = null;
    pc.close();
  }
  if (stream) {
    stream.getTracks().forEach(t => t.stop());
  }
}
function waitForIce(pc, timeoutMs) {
  return new Promise(resolve => {
    if (pc.iceGatheringState === 'complete') {
      resolve();
      return;
    }
    const handler = () => {
      if (pc.iceGatheringState === 'complete') {
        pc.removeEventListener('icegatheringstatechange', handler);
        resolve();
      }
    };
    pc.addEventListener('icegatheringstatechange', handler);
    setTimeout(() => {
      pc.removeEventListener('icegatheringstatechange', handler);
      resolve();
    }, timeoutMs);
  });
}
