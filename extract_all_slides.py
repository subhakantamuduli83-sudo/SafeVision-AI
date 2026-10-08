import sys
import re
sys.stdout.reconfigure(encoding='utf-8')

with open('presentation_slides.html', 'r', encoding='utf-8') as f:
    text = f.read()

slides = text.split('<section class="slide">')[1:7]

for idx, s in enumerate(slides, 1):
    s_clean = s.split('</section>')[0]
    s_clean = re.sub(r'src="data:image/[^"]+"', 'src="[IMAGE]"', s_clean)
    lines = []
    for line in s_clean.splitlines():
        t = re.sub(r'<[^>]+>', ' ', line).strip()
        t = " ".join(t.split())
        if t and not t.startswith('SafeVision AI • Industrial EHS') and not 'STPI & EmTek BPUT Hackathon • Slide' in t:
            lines.append(t)
    
    print(f"\n==================== SLIDE {idx} ====================")
    for l in lines:
        print("  ", l)
