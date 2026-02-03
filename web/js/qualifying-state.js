/**
 * Qualifying session state management.
 * Extends PlaybackState with lap telemetry tracking for graphs.
 */
import { PlaybackState } from "./state.js";

export class QualifyingState extends PlaybackState {
    constructor() {
        super();

        // Per-driver current lap telemetry: { distance: [], speed: [], throttle: [], brake: [] }
        this.currentLapTelemetry = {};

        // Per-driver last known lap number (to detect lap changes)
        this.driverLapNumbers = {};

        // Per-driver best lap times
        this.bestLapTimes = {};
    }

    /**
     * Update lap telemetry from the current frame.
     * Detects lap changes and resets telemetry arrays accordingly.
     */
    updateLapTelemetry(frame) {
        if (!frame || !frame.drivers) return;

        for (const [drv, st] of Object.entries(frame.drivers)) {
            const currentLap = st.l || 1;
            const prevLap = this.driverLapNumbers[drv];

            // Initialize telemetry storage for this driver if not present
            if (!this.currentLapTelemetry[drv]) {
                this.currentLapTelemetry[drv] = {
                    distance: [],
                    speed: [],
                    throttle: [],
                    brake: [],
                };
            }

            // Detect lap change - reset telemetry arrays
            if (prevLap !== undefined && currentLap !== prevLap) {
                this.currentLapTelemetry[drv] = {
                    distance: [],
                    speed: [],
                    throttle: [],
                    brake: [],
                };
            }

            // Update lap number tracking
            this.driverLapNumbers[drv] = currentLap;

            // Get distance in lap (di field from frame data)
            const distance = st.di || 0;
            const speed = st.s || 0;
            const throttle = st.t || 0;
            let brake = st.b || 0;
            // Normalize brake (might be 0-1 or 0-100)
            if (brake <= 1 && brake > 0) brake = brake * 100;

            // Avoid duplicate distance points (only add if distance increased)
            const telemetry = this.currentLapTelemetry[drv];
            const lastDist = telemetry.distance.length > 0
                ? telemetry.distance[telemetry.distance.length - 1]
                : -1;

            if (distance > lastDist) {
                telemetry.distance.push(distance);
                telemetry.speed.push(speed);
                telemetry.throttle.push(throttle);
                telemetry.brake.push(brake);
            }

            // Update best lap times from frame data if available
            // Best lap time is tracked in the frame's fastest lap data or driver's best time
            if (st.bt && (!this.bestLapTimes[drv] || st.bt < this.bestLapTimes[drv].time)) {
                this.bestLapTimes[drv] = {
                    time: st.bt,
                    lap: currentLap,
                };
            }
        }
    }

    /**
     * Get telemetry data for a specific driver.
     */
    getTelemetry(driver) {
        return this.currentLapTelemetry[driver] || {
            distance: [],
            speed: [],
            throttle: [],
            brake: [],
        };
    }

    /**
     * Get best lap time for a driver.
     */
    getBestLapTime(driver) {
        return this.bestLapTimes[driver]?.time || null;
    }

    /**
     * Clear all telemetry (e.g., on restart or seek).
     */
    clearTelemetry() {
        this.currentLapTelemetry = {};
        this.driverLapNumbers = {};
    }

    /**
     * Override restart to also clear telemetry.
     */
    restart() {
        super.restart();
        this.clearTelemetry();
    }

    /**
     * Override seekForward to also clear telemetry.
     */
    seekForward(seconds) {
        super.seekForward(seconds);
        this.clearTelemetry();
    }

    /**
     * Override seekBackward to also clear telemetry.
     */
    seekBackward(seconds) {
        super.seekBackward(seconds);
        this.clearTelemetry();
    }
}
