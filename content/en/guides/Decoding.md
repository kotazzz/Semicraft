---
title: Decoding Resources
tags:
  - guides
  - arg
aliases:
  - Research tools
lang: en
translation: guides/Декодирование
---

> 🌐 [[guides/Декодирование|Russian version]]

# Decoding Tools

Universal text cipher decoder: [CyberSwissKnife](https://kotazzz.github.io/CyberSwissKnife)

## Tool Table

| Example | Tool |
| --- | --- |
| Audio beep then noise | [SSTV Decoder](https://sstv-decoder.mathieurenaud.fr/) |
| Hidden frequencies in audio | [Spectrum Analyzer](https://academo.org/demos/spectrum-analyzer/) |
| String of 0 and 1 | [Binary Decoder](https://cryptii.com/pipes/binary-decoder) |
| HEX string | [Hex Decoder](https://cryptii.com/pipes/hex-decoder) |
| String ending with `=` | [Base64 Decode](https://www.base64decode.org/) |
| A–Z and 2–7 string | [Base32 Decode](https://emn178.github.io/online-tools/base32_decode.html) |
| Mixed ASCII symbols | [ROT-47](https://www.dcode.fr/rot-47-cipher) |
| Dots and dashes | [Morse Translator](https://morsecode.world/international/translator.html) |
| 11 ID-like symbols | [YouTube](https://www.youtube.com/watch?v=1234567890x) |

## Media Processing Tips

### Barcodes / QR

- Remove extra elements from the image
- Crop strictly to the code
- Increase contrast, reduce noise

### Images

- Brighten and increase contrast
- Check color inversion
- View individual RGB channels

### Audio

- Reverse, speed up/slow down, amplify volume
- Spectrogram
- Recommended tool: **Audacity**

### Text

- Reverse string, acrostic
- Analyze highlighted and "extra" letters
- Check case and repeating symbols

### Links and Identifiers

- 11 characters — likely a YouTube ID
- Imgur: `https://imgur.com/a/aaabbbc`
- Pastebin: `https://pastebin.com/aaabbbc`

### YouTube

Check: title, description, comments, subtitles, channel posts, playlists, channel description.

## File Type Identification

- `<!doctypehtml>` at start — rename to `.html`, open in browser
- `PK` in notepad — ZIP archive
