import sys
import re
sys.stdout.reconfigure(encoding='utf-8')

with open('presentation_slides.html', 'r', encoding='utf-8') as f:
    text = f.read()

s1 = text.split('<section class="slide">')[1].split('</section>')[0]
s1_clean = re.sub(r'src="data:image/[^"]+"', 'src="[IMAGE]"', s1)
for line in s1_clean.splitlines():
    t = re.sub(r'<[^>]+>', ' ', line).strip()
    t = " ".join(t.split())
    if t and not t.startswith('SafeVision AI •') and not 'STPI & EmTek' in t:
        print("  ", t)
