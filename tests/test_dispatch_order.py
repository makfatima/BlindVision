"""Haptic is sent before speech; SOS haptic fires immediately and interrupts
an utterance already in progress. Uses a fake engine, so this proves the
ordering logic only -- physical motor/speech timing still needs hardware."""
import sys, os, threading, time
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "smart_goggles"))
from audio import tts_engine
from config import Tier


class FakeEngine:
    def __init__(self, log):
        self.log, self.cb, self.stopped = log, None, False
    def setProperty(self, *a): pass
    def connect(self, name, cb): self.cb = cb
    def say(self, text): self.text = text
    def stop(self): self.stopped = True
    def runAndWait(self):
        self.stopped = False
        self.log.append(("speak_start", self.text))
        for _ in range(20):                 # 20 "words", 10 ms each
            if self.cb: self.cb("w", 0, 1)
            if self.stopped:
                self.log.append(("speak_cut", self.text)); return
            time.sleep(0.01)
        self.log.append(("speak_end", self.text))


class A:
    def __init__(self, tier, msg):
        self.tier, self.message, self.severity = tier, msg, "x"


def make(log):
    orig = tts_engine.pyttsx3
    class P:  # fake module
        @staticmethod
        def init(): return FakeEngine(log)
    tts_engine.pyttsx3 = P
    d = tts_engine.AlertDispatcher(haptic_send=lambda p: log.append(("haptic", p)))
    tts_engine.pyttsx3 = orig
    return d


def test_haptic_before_speech():
    log = []
    d = make(log)
    d.dispatch(A(Tier.MEDIUM, "chair ahead"))
    time.sleep(0.4)
    assert log[0] == ("haptic", "single_pulse")
    assert log[1] == ("speak_start", "chair ahead")


def test_sos_preempts_utterance_in_progress():
    log = []
    d = make(log)
    d.dispatch(A(Tier.MEDIUM, "chair ahead"))
    time.sleep(0.05)                        # mid-utterance
    d.dispatch(A(Tier.SOS, "SOS"))
    time.sleep(0.5)
    assert ("speak_cut", "chair ahead") in log
    i_sos_h = log.index(("haptic", "sos_three_pulse"))
    i_cut = log.index(("speak_cut", "chair ahead"))
    assert i_sos_h < i_cut                  # SOS haptic did not wait for speech
    assert ("speak_end", "SOS") in log
    assert log.count(("haptic", "sos_three_pulse")) == 1
