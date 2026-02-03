/**
 * Chunk-based data loading with delta reconstruction.
 *
 * Loads chunks on demand, preloads ahead, evicts old chunks.
 * Reconstructs delta-encoded fields (weather, track_status, fastest_lap, overall_bests).
 */

const PRELOAD_AHEAD = 3;
const EVICT_BEHIND = 5;

export class DataLoader {
    constructor() {
        this.manifest = null;
        this.track = null;
        this.basePath = "";

        // chunk index -> array of compact frames
        this.chunks = new Map();
        // chunk index -> Promise (loading in progress)
        this.loading = new Map();

        this.chunkSize = 1000;
        this.chunkCount = 0;

        // Reconstructed state for delta fields (per-chunk first frame carries full state)
        // We keep per-chunk "entry state" so we can reconstruct any frame quickly.
        this.chunkEntryStates = new Map();
    }

    async loadSession(sessionDir, onProgress) {
        this.basePath = `data/${sessionDir}`;

        // Load manifest
        if (onProgress) onProgress("Loading manifest...", 0);
        const manifestResp = await fetch(`${this.basePath}/manifest.json`);
        this.manifest = await manifestResp.json();
        this.chunkSize = this.manifest.chunkSize;
        this.chunkCount = this.manifest.chunkCount;

        // Load track
        if (onProgress) onProgress("Loading track...", 10);
        const trackResp = await fetch(`${this.basePath}/track.json`);
        this.track = await trackResp.json();

        // Preload first chunk
        if (onProgress) onProgress("Loading initial data...", 20);
        await this.loadChunk(0);

        if (onProgress) onProgress("Ready", 100);
        return this.manifest;
    }

    /**
     * Get a fully-reconstructed frame by global index.
     * Returns null if chunk is not yet loaded.
     */
    getFrame(globalIdx) {
        const chunkIdx = Math.floor(globalIdx / this.chunkSize);
        const localIdx = globalIdx % this.chunkSize;

        const chunk = this.chunks.get(chunkIdx);
        if (!chunk) {
            // Trigger load
            this.ensureChunk(chunkIdx);
            return null;
        }

        if (localIdx >= chunk.length) return null;

        // Reconstruct delta fields
        return this._reconstructFrame(chunkIdx, localIdx, chunk);
    }

    /**
     * Ensure a chunk is loaded, trigger preload of upcoming chunks, evict old ones.
     */
    ensureChunk(chunkIdx) {
        // Load requested chunk
        this.loadChunk(chunkIdx);

        // Preload ahead
        for (let i = 1; i <= PRELOAD_AHEAD; i++) {
            const ahead = chunkIdx + i;
            if (ahead < this.chunkCount) {
                this.loadChunk(ahead);
            }
        }

        // Evict old chunks
        for (const loadedIdx of this.chunks.keys()) {
            if (loadedIdx < chunkIdx - EVICT_BEHIND) {
                this.chunks.delete(loadedIdx);
                this.chunkEntryStates.delete(loadedIdx);
            }
        }
    }

    async loadChunk(chunkIdx) {
        if (this.chunks.has(chunkIdx)) return;
        if (this.loading.has(chunkIdx)) return this.loading.get(chunkIdx);

        const promise = (async () => {
            try {
                const fname = `chunk_${String(chunkIdx).padStart(3, "0")}.json`;
                const resp = await fetch(`${this.basePath}/${fname}`);
                const frames = await resp.json();
                this.chunks.set(chunkIdx, frames);
                this._buildEntryState(chunkIdx, frames);
            } catch (e) {
                console.error(`Failed to load chunk ${chunkIdx}:`, e);
            } finally {
                this.loading.delete(chunkIdx);
            }
        })();

        this.loading.set(chunkIdx, promise);
        return promise;
    }

    /**
     * Build the "entry state" for a chunk by scanning its first frame's delta fields.
     * Each chunk's first frame always includes full delta-encoded fields.
     */
    _buildEntryState(chunkIdx, frames) {
        if (frames.length === 0) return;
        const first = frames[0];
        this.chunkEntryStates.set(chunkIdx, {
            w: first.w || null,
            ts: first.ts || "GREEN",
            fl: first.fl || null,
            ob: first.ob || null,
        });
    }

    /**
     * Reconstruct a fully populated frame from compact + delta state.
     */
    _reconstructFrame(chunkIdx, localIdx, chunk) {
        const compact = chunk[localIdx];

        // Get entry state for this chunk
        let state = this.chunkEntryStates.get(chunkIdx);
        if (!state) {
            state = { w: null, ts: "GREEN", fl: null, ob: null };
        }

        // Walk from start of chunk to localIdx to reconstruct delta state
        // (We cache the entry state, then apply deltas up to localIdx)
        let weather = state.w;
        let trackStatus = state.ts;
        let fastestLap = state.fl;
        let overallBests = state.ob;

        // Apply deltas from frame 1 (frame 0 is the entry state) up to localIdx
        for (let i = 1; i <= localIdx; i++) {
            const f = chunk[i];
            if (f.w !== undefined) weather = f.w;
            if (f.ts !== undefined) trackStatus = f.ts;
            if (f.fl !== undefined) fastestLap = f.fl;
            if (f.ob !== undefined) overallBests = f.ob;
        }

        // Also check current frame
        if (compact.w !== undefined) weather = compact.w;
        if (compact.ts !== undefined) trackStatus = compact.ts;
        if (compact.fl !== undefined) fastestLap = compact.fl;
        if (compact.ob !== undefined) overallBests = compact.ob;

        // Build reconstructed frame
        return {
            t: compact.t,
            drivers: compact.dr,
            weather: weather ? {
                AirTemp: weather.at,
                TrackTemp: weather.tt,
                Humidity: weather.hu,
                Rainfall: weather.rf,
                WindSpeed: weather.ws,
            } : {},
            trackStatus: trackStatus || "GREEN",
            fastestLap: fastestLap ? {
                driver: fastestLap.dr,
                time: fastestLap.tm,
                lapNum: fastestLap.ln,
                isNew: fastestLap.nw,
            } : null,
            overallBests: overallBests ? {
                s1: overallBests.s1,
                s2: overallBests.s2,
                s3: overallBests.s3,
                lap: overallBests.lp,
                fastestDriver: overallBests.fd,
                fastestLapNum: overallBests.fn,
            } : null,
            positionChanges: compact.pc ? compact.pc.map(c => ({
                driver: c.dr,
                fromPos: c.fp,
                toPos: c.tp,
                passed: c.pa,
                t: c.t,
            })) : [],
            raceMessages: compact.rm ? compact.rm.map(m => ({
                type: m.ty,
                driver: m.dr,
                message: m.mg,
                age: m.ag,
            })) : [],
        };
    }
}
