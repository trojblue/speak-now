import time
import requests
import pyaudio
import numpy as np


# ---------------------------------------------------------------------
# HELPER FUNCTIONS
# ---------------------------------------------------------------------
def generate_gemini(prompt, api_key, model):
    """Generates content using Google's Generative Language API."""
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    headers = {"Content-Type": "application/json"}
    params = {"key": api_key}
    data = {
        "contents": [
            {"parts": [{"text": prompt}]},
        ],
    }
    response = requests.post(url, json=data, headers=headers, params=params)

    if response.status_code != 200:
        raise Exception(f"API request failed: {response.status_code} - {response.text}")

    try:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError) as e:
        raise ValueError("Unexpected API response format") from e


class MinimalSoundEngine:
    """Modern, minimalist sound engine with subtle, elegant feedback tones."""
    
    def __init__(self):
        self.sample_rate = 48000  # Higher sample rate for cleaner sound
        self.p = pyaudio.PyAudio()
    
    def _apply_envelope(self, audio, attack=0.01, release=0.01):
        """Apply smooth attack and release envelope."""
        total_samples = len(audio)
        attack_samples = int(attack * self.sample_rate)
        release_samples = int(release * self.sample_rate)
        
        # Create smooth envelope using half-cosine windows for more elegant transitions
        envelope = np.ones(total_samples)
        if attack_samples > 0:
            envelope[:attack_samples] = (1 - np.cos(np.linspace(0, np.pi, attack_samples))) / 2
        if release_samples > 0:
            envelope[-release_samples:] = (1 + np.cos(np.linspace(0, np.pi, release_samples))) / 2
            
        return audio * envelope
    
    def sine(self, frequency, duration, volume=0.3, attack=0.008, release=0.015):
        """Generate a clean sine wave with smooth envelope."""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        tone = np.sin(2 * np.pi * frequency * t)
        tone = self._apply_envelope(tone, attack, release)
        tone *= volume
        return (tone * 32767).astype(np.int16)
    
    def synth_tone(self, frequency, duration, volume=0.25, harmonics=None, attack=0.01, release=0.02):
        """Generate a richer tone with harmonics for more sophisticated sound."""
        if harmonics is None:
            # Default harmonic structure for a warm, pleasant tone
            harmonics = [(1.0, 1.0), (2.0, 0.15), (3.0, 0.05)]
            
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        tone = np.zeros_like(t)
        
        # Add fundamental and harmonics
        for harmonic_ratio, amplitude in harmonics:
            tone += amplitude * np.sin(2 * np.pi * (frequency * harmonic_ratio) * t)
        
        # Normalize
        tone = tone / max(abs(tone))
        tone = self._apply_envelope(tone, attack, release)
        tone *= volume
        return (tone * 32767).astype(np.int16)
    
    def glass_tone(self, frequency, duration, volume=0.25, attack=0.004, release=0.08):
        """Creates a clean, glass-like tone - modern and understated."""
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        
        # Create a tone that mimics striking glass
        tone = np.sin(2 * np.pi * frequency * t)
        
        # Add a subtle higher frequency component
        tone += 0.1 * np.sin(2 * np.pi * frequency * 2.997 * t)
        
        # Add very subtle noise at the attack for realism
        noise_duration = int(0.01 * self.sample_rate)
        if noise_duration > 0:
            noise = np.random.uniform(-0.02, 0.02, noise_duration)
            noise = np.pad(noise, (0, len(tone) - len(noise)), 'constant')
            tone += noise
            
        tone = self._apply_envelope(tone, attack, release)
        tone *= volume
        return (tone * 32767).astype(np.int16)
    
    def multi_tone(self, frequencies, duration, volume=0.3, relative_volumes=None, attack=0.01, release=0.02):
        """Play multiple frequencies simultaneously with balanced volumes."""
        if relative_volumes is None:
            relative_volumes = [1.0] * len(frequencies)
            
        t = np.linspace(0, duration, int(self.sample_rate * duration), False)
        tone = np.zeros_like(t)
        
        # Add each frequency component
        for i, freq in enumerate(frequencies):
            rel_vol = relative_volumes[i] if i < len(relative_volumes) else 1.0
            tone += rel_vol * np.sin(2 * np.pi * freq * t)
            
        # Normalize
        max_val = max(abs(tone))
        if max_val > 0:
            tone = tone / max_val
            
        tone = self._apply_envelope(tone, attack, release)
        tone *= volume
        return (tone * 32767).astype(np.int16)
    
    def play(self, audio_data):
        """Play audio through speakers."""
        stream = self.p.open(format=pyaudio.paInt16, 
                             channels=1, 
                             rate=self.sample_rate, 
                             output=True)
        stream.write(audio_data.tobytes())
        stream.stop_stream()
        stream.close()
    
    def close(self):
        """Clean up PyAudio resources."""
        self.p.terminate()


# Create a global sound engine instance
sound_engine = MinimalSoundEngine()


def play_sound(sound_type, volume=0.5):
    """Play sophisticated, minimal sounds based on the action type."""
    try:
        # Modern UI scale frequencies - based on pentatonic scale for pleasant harmony
        # These align better with the sleek, modern aesthetic of the CSS
        # D4, F#4, A4, B4, D5 pentatonic notes (587.33, 739.99, 880.00, 987.77, 1174.66 Hz)
        
        if sound_type == "startup":
            # Elegant startup sound sequence using glass tones
            sound1 = sound_engine.glass_tone(587.33, 0.08, volume * 0.8, attack=0.005)
            sound2 = sound_engine.glass_tone(739.99, 0.08, volume * 0.85, attack=0.004)
            sound3 = sound_engine.glass_tone(880.00, 0.12, volume * 0.9, attack=0.003, release=0.1)
            
            # Add slight delay between tones
            delay = np.zeros(int(0.02 * sound_engine.sample_rate), dtype=np.int16)
            result = np.concatenate([sound1, delay, sound2, delay, sound3])
            
            sound_engine.play(result)
            
        elif sound_type == "text_added":
            # Subtle, clean notification
            sound_engine.play(sound_engine.sine(1174.66, 0.07, volume * 0.6, attack=0.004, release=0.06))
            
        elif sound_type == "processing":
            # Minimal processing indicator
            sound_engine.play(sound_engine.glass_tone(739.99, 0.05, volume * 0.4, attack=0.003, release=0.04))
            
        elif sound_type == "paste_raw":
            # Two harmonious notes for paste action
            harmonics = [(1.0, 1.0), (2.0, 0.08), (3.0, 0.03)]
            sound = sound_engine.synth_tone(587.33, 0.1, volume * 0.6, harmonics, attack=0.005, release=0.08)
            sound_engine.play(sound)
            
        elif sound_type == "paste_formatted":
            # More sophisticated paste formatted sound with multiple tones
            sound_engine.play(sound_engine.multi_tone(
                [739.99, 987.77], 
                0.12, 
                volume * 0.6, 
                relative_volumes=[1.0, 0.7], 
                attack=0.008, 
                release=0.1
            ))
            
        elif sound_type == "error":
            # Subtle but clear error indication using minor notes
            sound_engine.play(sound_engine.multi_tone(
                [554.37, 659.25],  # C#5, E5 - minor third interval
                0.15, 
                volume * 0.5, 
                relative_volumes=[0.7, 1.0], 
                attack=0.004, 
                release=0.12
            ))
            
        elif sound_type == "toggle_recording":
            # Clean toggle sound
            sound_engine.play(sound_engine.glass_tone(880.00, 0.08, volume * 0.6, attack=0.003, release=0.07))
            
    except Exception as e:
        print(f"Sound error: {e}")


# Cleanup function to call when shutting down
def cleanup_audio():
    sound_engine.close()


# Example usage:
# play_sound("startup", volume=0.6)  # Play startup sound at 60% volume
# play_sound("text_added", volume=0.5)  # Play notification at 50% volume