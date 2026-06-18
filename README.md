# Morse Code Blinker 👁️👁️
### Blink based Morse code communication using computer vision

---

## 📌 Overview
Morse Code Blinker is a computer vision based assistive application that converts eye blinks into Morse code and translates them into readable text and speech. Using a webcam and facial landmark detection the system enables hands free communication through controlled eye blinks.

This project explores human computer interaction accessibility and real time computer vision.

---

## ✨ Features
- Real time eye blink detection  
- Converts blinks into Morse code dots and dashes  
- Translates Morse code into readable text  
- Automatic letter and word detection using pauses  
- Spell correction for improved readability  
- Text to speech output  
- Gesture based word deletion using one eye  
- Message reset when face is not detected  
- On screen visual feedback  

---

## 🛠️ Technologies Used
- Python  
- OpenCV  
- CVZone  
- Face Mesh Detection  
- PySpellChecker  
- Text to Speech using Windows SAPI or pyttsx3  

---

## ⚙️ How It Works
- Short blink represents a dot  
- Long blink represents a dash  
- Pause between blinks completes a letter  
- Longer pause completes a word  
- One eye visible for a duration deletes the last word  
- Eyes closed for a longer duration resets the message  

---

## 📦 Installation
1. Clone the repository  
2. Install the required dependencies  

```bash
pip install opencv-python cvzone pyspellchecker pyttsx3
