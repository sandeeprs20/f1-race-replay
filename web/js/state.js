/**
 * Playback state management.
 */
export class PlaybackState {
    constructor() {
        this.frameIdx = 0;
        this.paused = true;
        this.speedChoices = [0.5, 1.0, 2.0, 4.0, 8.0, 16.0, 32.0, 64.0];
        this.speedIndex = 1;

        this.showUI = true;
        this.showProgressBar = true;
        this.leaderboardCollapsed = false;
        this.speedTrapCollapsed = false;

        this.selectedDriver = null;
        this.hoverIndex = null;

        // Fastest lap tracking (persists across frames)
        this.fastestLapDriver = null;
        this.fastestLapTime = Infinity;

        // Overtake feed (accumulates over time)
        this.recentOvertakes = [];

        // Manifest data
        this.manifest = null;
        this.fps = 25;
        this.totalFrames = 0;
    }

    get speed() {
        return this.speedChoices[this.speedIndex];
    }

    speedUp() {
        this.speedIndex = Math.min(this.speedIndex + 1, this.speedChoices.length - 1);
    }

    speedDown() {
        this.speedIndex = Math.max(this.speedIndex - 1, 0);
    }

    seekForward(seconds) {
        this.frameIdx = Math.min(this.frameIdx + this.fps * seconds, this.totalFrames - 1);
    }

    seekBackward(seconds) {
        this.frameIdx = Math.max(this.frameIdx - this.fps * seconds, 0);
    }

    restart() {
        this.frameIdx = 0;
        this.paused = false;
    }

    togglePause() {
        this.paused = !this.paused;
    }

    advance(framesPerTick) {
        if (this.paused) return;
        this.frameIdx += framesPerTick;
        if (this.frameIdx >= this.totalFrames - 1) {
            this.frameIdx = this.totalFrames - 1;
            this.paused = true;
        }
    }
}
