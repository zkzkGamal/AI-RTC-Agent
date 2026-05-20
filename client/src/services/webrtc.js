/**
 * webrtc.js — WebRTC service for managing peer connections
 */

const ICE_SERVERS = [{ urls: 'stun:stun.l.google.com:19302' }]

/**
 * Create an RTCPeerConnection, attach a microphone audio track,
 * generate an SDP offer, and wait for ICE gathering.
 *
 * @param {function} onStateChange  - called with (connectionState: string)
 * @returns {{ pc: RTCPeerConnection, stream: MediaStream, offer: RTCSessionDescriptionInit }}
 */
export async function createConnection(onStateChange, onMessage) {
  // 1. Get microphone stream (audio only)
  const stream = await navigator.mediaDevices.getUserMedia({
    audio: {
      echoCancellation: true,
      noiseSuppression: true,
      autoGainControl: true,
      sampleRate: 48000,
    },
    video: false,
  })

  // 2. Create peer connection
  const pc = new RTCPeerConnection({ iceServers: ICE_SERVERS })

  // Create DataChannel for live transcript
  const dc = pc.createDataChannel('transcript', { ordered: true })
  dc.onmessage = (event) => {
    onMessage?.(event.data)
  }
  dc.onopen = () => console.log("DataChannel ('transcript') opened")
  dc.onclose = () => console.log("DataChannel ('transcript') closed")

  // 3. Monitor connection state
  pc.onconnectionstatechange = () => {
    onStateChange?.(pc.connectionState)
  }

  // 4. Add audio track
  stream.getAudioTracks().forEach((track) => pc.addTrack(track, stream))

  // 5. Create offer
  const offer = await pc.createOffer()
  await pc.setLocalDescription(offer)

  // 6. Wait for ICE gathering (max 3s)
  await waitForIce(pc, 3000)

  return {
    pc,
    stream,
    offer: { sdp: pc.localDescription.sdp, type: pc.localDescription.type },
  }
}

/**
 * Apply the server's SDP answer to the peer connection.
 */
export async function applyAnswer(pc, answer) {
  await pc.setRemoteDescription(new RTCSessionDescription(answer))
}

/**
 * Cleanly close a peer connection and stop all media tracks.
 */
export function closeConnection(pc, stream) {
  if (pc) {
    pc.onconnectionstatechange = null
    pc.close()
  }
  if (stream) {
    stream.getTracks().forEach((t) => t.stop())
  }
}

// ─── Helpers ──────────────────────────────────────────────────────

function waitForIce(pc, timeoutMs) {
  return new Promise((resolve) => {
    if (pc.iceGatheringState === 'complete') {
      resolve()
      return
    }
    const handler = () => {
      if (pc.iceGatheringState === 'complete') {
        pc.removeEventListener('icegatheringstatechange', handler)
        resolve()
      }
    }
    pc.addEventListener('icegatheringstatechange', handler)
    setTimeout(() => {
      pc.removeEventListener('icegatheringstatechange', handler)
      resolve()
    }, timeoutMs)
  })
}
