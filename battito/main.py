import threading
import time

import mido


#: Nanoseconds per minute
NS_PER_MIN = 60_000_000_000
NS_PER_SEC = 1_000_000_000


class Sequencer:
    def __init__(self, sequence, intervals=16):
        self.sequence = sequence
        self.intervals = intervals
        self.beat_count = -1

    def step(self):
        idx = self.beat_count = (self.beat_count + 1) % self.intervals
        if idx == 0:
            print('}')
        if self.sequence[idx] > 0:
            print('#', end='', flush=True)
        else:
            print(' ', end='', flush=True)


class Beat:
    def __init__(self, bpm, callback, intervals=16):
        self.intervals = intervals
        self.callback = callback
        self.set_bpm(bpm)
        self.stop_requested = False

    def set_bpm(self, bpm):
        self.bpm = bpm
        self.interval_ns = NS_PER_MIN // self.bpm // self.intervals
        self.beat_count = 0
        print('SET BPM', bpm)

    def run(self):
        first_ns = last_ns = time.monotonic_ns()
        count = 0
        while not self.stop_requested:
            now_ns = time.monotonic_ns()
            rem_ns = (last_ns + self.interval_ns) - now_ns
            if rem_ns <= 0:
                self.beat_count = (self.beat_count + 1) % self.intervals
                if self.beat_count == 0:
                    count += 1
                self.callback()
                last_ns += self.interval_ns
            else:
                # Sleep almost to the next beat
                time.sleep(rem_ns * 0.925 / NS_PER_SEC)

            if count == 30:
                now_ns = time.monotonic_ns()
                print('elapsed', (now_ns - first_ns) / NS_PER_SEC)


class TempoKeeper:

    RESET_AFTER_SECS = 2

    def __init__(self, bpm=120):
        self.bpm = bpm
        self.last_ns = -self.RESET_AFTER_SECS * NS_PER_SEC
        self.intervals = []

    def tap(self):
        now_ns = time.monotonic_ns()
        interval_ns = now_ns - self.last_ns
        self.last_ns = now_ns
        if interval_ns > self.RESET_AFTER_SECS * NS_PER_SEC:
            self.intervals = []
            self.bpm = -1
            #print('RESTART')
        else:
            self.intervals.append(interval_ns)
            if len(self.intervals) > 2:
                avg_interval_ns = sum(self.intervals) / len(self.intervals)
                self.bpm = int(NS_PER_MIN / avg_interval_ns)
                #print('tempo estimated', self.bpm, self.intervals)


class BeatController:
    def __init__(self, beat, tempo):
        self.beat = beat
        self.tempo = tempo
        self.in_port = mido.open_input('Midi Fighter Twister', callback=self.handle_midi_in)

    def start_beat(self):
        t = threading.Thread(target=beat.run)
        t.start()

    def stop_beat(self):
        self.beat.stop_requested = True

    def tempo_tap(self):
        self.tempo.tap()
        if self.tempo.bpm > 0:
            self.beat.set_bpm(self.tempo.bpm)

    def handle_midi_in(self, message):
        dial = message.control
        value = message.value
        channel = message.channel
        if channel == 1:
            if value == 127:
                if dial == 15:
                    self.stop_beat()
                    print('QUIT')
                elif dial == 0:
                    self.tempo_tap()
                else:
                    print('CLICK IN', dial)



# TODO: press/turn knob to adjust tempo slightly
# TODO: turn knob to slightly anticipate / posticipate the beat and match the music


if __name__ == '__main__':
    sequence = [1, 0, 0, 0, 0, 0, 0, 0, 1, 0, 1, 0, 0, 0, 0, 0]
    sequencer = Sequencer(sequence, intervals=16)

    tempo = TempoKeeper()
    beat = Beat(bpm=120, intervals=16, callback=sequencer.step)
    controller = BeatController(beat, tempo)
    controller.start_beat()
