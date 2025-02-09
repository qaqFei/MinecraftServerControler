from __future__ import annotations

import typing
from copy import deepcopy

__all__ = (
    "MidiFile",
    "MidiParseError",
    "Track"
)

class ByteReader:
    def __init__(self, data: bytes):
        self.data = data
        self.index = 0
    
    def read(self, n: int):
        result = self.data[self.index:self.index + n]
        self.index += n
        
        if len(result) != n:
            raise EOFError(f"Unexpected EOF")
        
        return result
    
    def read_int(self, n: int, byteorder: typing.Literal["little", "big"]):
        return int.from_bytes(self.read(n), byteorder=byteorder)
    
    def read_short(self):
        return self.read_int(2, "big")
    
    def read_dynamic_int(self):
        result = bytearray()
        while True:
            byte = self.read(1)[0]
            result.append(byte & 0x7F)
            if byte & 0x80 == 0: break
        zfilled = "".join(list(map(lambda x, i: bin(x)[2:] if i == 0 else bin(x)[2:].zfill(7), result, range(len(result)))))
        return int(zfilled, 2) if zfilled else 0
    
    def seek_by(self, n: int):
        self.index += n

class MidiParseError(Exception): ...

class MidiFile:
    def __init__(self, data: bytes):
        self.reader = ByteReader(data)
        try: self._parse()
        except Exception as e:
            raise MidiParseError("Bad MIDI file") from e
    
    def _parse(self):
        magic = self.reader.read(4)
        if magic != b"MThd":
            raise MidiParseError(f"Bad MIDI magic: {magic}")
        
        self.header_length = self.reader.read_int(4, "big")
        self.format = self.reader.read_short()
        
        if self.format not in (0, 1, 2):
            raise MidiParseError(f"Bad MIDI format: {self.format}")

        self.n_tracks = self.reader.read_short()
        self.base_time = bin(self.reader.read_short())[2:].zfill(16)
        self.time_format = int(self.base_time[0], 2)
        self.base_time = self.base_time[1:]
        
        match self.time_format:
            case 0:
                self.tick_per_quarter_note = int(self.base_time, 2)
            
            case 1:
                self.frame_per_second = int(self.base_time[:7], 2)
                self.tick_per_frame = int(self.base_time[7:], 2)
                
                match self.frame_per_second:
                    case -24 | -25 | -30:
                        self.frame_per_second *= -1
                    
                    case -29:
                        self.frame_per_second = 29.97
                
                self.tick_per_second = self.frame_per_second * self.tick_per_frame
                
                raise MidiParseError("Unsupported time format")
            
            case _:
                assert False, "Invalid time format"
        
        self.tracks: list[Track[dict]] = [self._parse_track() for _ in range(self.n_tracks)]
        self._init_msgs()
    
    def _parse_track(self):
        magic = self.reader.read(4)
        if magic != b"MTrk":
            raise MidiParseError(f"Bad MIDI track magic: {magic}")
        
        msgs: Track[dict] = Track()
        track_length = self.reader.read_int(4, "big")
        track_data = self.reader.read(track_length)
        track_reader = ByteReader(track_data)
        
        while track_reader.index < len(track_data):
            delta_time = track_reader.read_dynamic_int()
            msg_type = track_reader.read(1)[0]
            if msg_type & 0x80 == 0:
                track_reader.seek_by(-1)
                msg_type = msgs[-1]["_type"]
                
            msg_strtype = hex(msg_type)[2:].zfill(2).upper()
            
            if msg_strtype == "FF":
                meta_type = track_reader.read(1)[0]
                msg_data = track_reader.read(track_reader.read_dynamic_int())
                msg = {"type": "meta"}
                
                match meta_type:
                    case 0x00:
                        msg["meta_type"] = "sequence_number"
                        msg["sound_number"] = int.from_bytes(msg_data, "big")
                    
                    case 0x01:
                        msg["meta_type"] = "text"
                        msg["text"] = msg_data
                    
                    case 0x02:
                        msg["meta_type"] = "copyright"
                        msg["copyright"] = msg_data
                    
                    case 0x03:
                        msg["meta_type"] = "sequence_name"
                        msg["sequence_name"] = msg_data
                    
                    case 0x04:
                        msg["meta_type"] = "instrument_name"
                        msg["instrument_name"] = msg_data
                    
                    case 0x05:
                        msg["meta_type"] = "lyric"
                        msg["lyric"] = msg_data
                    
                    case 0x06:
                        msg["meta_type"] = "marker"
                        msg["marker"] = msg_data
                    
                    case 0x07:
                        msg["meta_type"] = "cue_point"
                        msg["cue_point"] = msg_data
                    
                    case 0x20:
                        msg["meta_type"] = "midi_channel_prefix"
                        msg["midi_channel_prefix"] = int.from_bytes(msg_data, "big")
                    
                    case 0x2F:
                        msg["meta_type"] = "end_of_track"
                        msg["end_of_track"] = True
                    
                    case 0x51:
                        msg["meta_type"] = "set_tempo"
                        msg["tempo"] = int.from_bytes(msg_data, "big")
                    
                    case 0x54:
                        msg["meta_type"] = "smpte_offset"
                        msg["smpte_offset"] = msg_data
                    
                    case 0x58:
                        msg["meta_type"] = "time_signature"
                        ints = list(msg_data)
                        msg["time_signature"] = ints[0] / ints[1]
                        msg["metronome_clock"] = ints[2]
                        msg["128th_note_per_beat"] = ints[3]
                    
                    case 0x59:
                        msg["meta_type"] = "key_signature"
                        msg["key_signature"] = msg_data
                    
                    case 0x7F:
                        msg["meta_type"] = "sequencer_specific"
                        msg["sequencer_specific"] = msg_data
                    
                    case _:
                        msg["meta_type"] = "meta_type_unknown"
                        msg["meta_type_unknown"] = meta_type
                        msg["meta_data"] = msg_data
                
            elif msg_strtype == "F0":
                msg_data = track_reader.read(track_reader.read_dynamic_int())
                msg = {"type": "sysex_message", "data": msg_data}

            elif msg_strtype[0] == "8":
                channel = int(msg_strtype[1], 16)
                note = track_reader.read(1)[0]
                velocity = track_reader.read(1)[0]
                msg = {"type": "note_off", "channel": channel, "note": note, "velocity": velocity}
            
            elif msg_strtype[0] == "9":
                channel = int(msg_strtype[1], 16)
                note = track_reader.read(1)[0]
                velocity = track_reader.read(1)[0]
                msg = {"type": "note_on", "channel": channel, "note": note, "velocity": velocity}
            
            elif msg_strtype[0] == "A":
                channel = int(msg_strtype[1], 16)
                note = track_reader.read(1)[0]
                velocity = track_reader.read(1)[0]
                msg = {"type": "note_aftertouch", "channel": channel, "note": note, "velocity": velocity}
                
            elif msg_strtype[0] == "B":
                channel = int(msg_strtype[1], 16)
                con_number = track_reader.read(1)[0]
                con_value = track_reader.read(1)[0]
                msg = {"type": "controller_change", "channel": channel, "controller_number": con_number, "controller_value": con_value}
            
            elif msg_strtype[0] == "C":
                channel = int(msg_strtype[1], 16)
                value = track_reader.read(1)[0]
                msg = {"type": "program_change", "channel": channel, "program_number": value}
            
            elif msg_strtype[0] == "D":
                channel = int(msg_strtype[1], 16)
                value = track_reader.read(1)[0]
                msg = {"type": "channel_aftertouch", "channel": channel, "value": value}
            
            elif msg_strtype[0] == "E":
                channel = int(msg_strtype[1], 16)
                note = track_reader.read(1)[0]
                value = track_reader.read(1)[0]
                msg = {"type": "pitch_bend", "channel": channel, "note": note, "value": value}
            
            msg["delta_time"] = delta_time
            msg["_type"] = msg_type
            msgs.append(msg)
        
        for msg in msgs:
            msg.pop("_type")
        
        return msgs

    def _init_msgs(self):
        for track in self.tracks:
            t = 0
            for msg in track:
                t += msg["delta_time"]
                msg["now_time"] = t
                msg["now_beat"] = t / self.tick_per_quarter_note
                
        if self.format != 2:
            globalBpmList = [{
                "time": msg["now_beat"],
                "bpm": 6e7 / msg["tempo"]
            } for track in self.tracks for msg in track if msg["type"] == "meta" and msg["meta_type"] == "set_tempo"]
            for track in self.tracks:
                track.bpmList.extend(deepcopy(globalBpmList))
        else:
            for track in self.tracks:
                track.bpmList.extend(({
                    "time": msg["now_beat"],
                    "bpm": 6e7 / msg["tempo"]
                } for msg in track if msg["type"] == "meta" and msg["meta_type"] == "set_tempo"))
        
        for track in self.tracks:
            for i, msg in enumerate(track):
                msg["sec_time"] = MidiFile.tick2second(msg["now_time"], track, self.tick_per_quarter_note)
                if i != 0:
                    msg["track_sec_delta"] = msg["sec_time"] - track[i - 1]["sec_time"]
                else:
                    msg["track_sec_delta"] = msg["sec_time"]
        
        sorted_msgs = sorted((j for i in self.tracks for j in i), key=lambda x: x["sec_time"])
        for i, msg in enumerate(sorted_msgs):
            if i != 0:
                msg["global_sec_delta"] = msg["sec_time"] - sorted_msgs[i - 1]["sec_time"]
            else:
                msg["global_sec_delta"] = msg["sec_time"]
        
        self.second_length = sorted_msgs[-1]["sec_time"]
                    
    @staticmethod
    def second2tick(t: int|float, track: Track, tick_per_quarter_note: int) -> float:
        beat = 0.0
        for i, e in enumerate(track.bpmList):
            sec_per_beat = 60 / e["bpm"]
            if i != len(track.bpmList) - 1:
                et_beat = track.bpmList[i + 1]["time"] - e["time"]
                et_sec = et_beat * sec_per_beat
                
                if t >= et_sec:
                    beat += et_beat
                    t -= et_sec
                else:
                    beat += t / sec_per_beat
                    return beat
            else:
                beat += t / sec_per_beat
        return beat * tick_per_quarter_note
    
    @staticmethod
    def tick2second(t: int|float, track: Track, tick_per_quarter_note: int) -> float:
        t /= tick_per_quarter_note
        sec = 0.0
        for i, e in enumerate(track.bpmList):
            sec_per_beat = 60 / e["bpm"]
            if i != len(track.bpmList) - 1:
                et_beat = track.bpmList[i + 1]["time"] - e["time"]
                
                if t >= et_beat:
                    sec += et_beat * sec_per_beat
                    t -= et_beat
                else:
                    sec += t * sec_per_beat
                    return sec
            else:
                sec += t * sec_per_beat
        return sec
    
    def play(self):
        msgs = [msg for track in self.tracks for msg in track]
        msgs.sort(key=lambda msg: msg["sec_time"])
        for msg in msgs: yield msg

class Track(list):
    def __init__(self):
        list.__init__(self)
        self.bpmList = []
