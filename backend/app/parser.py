"""Parse one-expert transcripts without rewriting source text."""
import re

MAX_BYTES = 2 * 1024 * 1024
STAMP = re.compile(r'(?m)^[ \t]*(\d{2,}:\d{2}(?::\d{2})?)[ \t]*\r?$')

def parse_transcript(raw: bytes, filename: str) -> dict:
    if not filename.lower().endswith('.txt'):
        raise ValueError('Choose a .txt transcript.')
    if len(raw) > MAX_BYTES:
        raise ValueError('Each transcript must be 2 MB or smaller.')
    try:
        source = raw.decode('utf-8-sig')
    except UnicodeDecodeError:
        raise ValueError('Save the transcript as UTF-8 text.') from None
    if not source.strip() or '\x00' in source:
        raise ValueError('The file is empty or is not plain text.')
    stamps = list(STAMP.finditer(source))
    if not stamps:
        raise ValueError('Add timestamp lines such as 00:18 before each passage.')
    header = source[:stamps[0].start()]
    fields = {}
    consumed = []
    for key, pattern in {
        'expert': r'^Expert(?:[ \t]+ID)?(?:[ \t]+\d+)?[ \t]*(?:[–—-]|:)[ \t]*([^\r\n]+?)[ \t]*\r?$',
        'role': r'^Role:[ \t]*([^\r\n]+?)[ \t]*\r?$',
        'market': r'^Market:[ \t]*([^\r\n]+?)[ \t]*\r?$',
    }.items():
        m = re.search(pattern, header, re.MULTILINE | re.IGNORECASE)
        if key == 'market' and not m and re.search(r'^Expert ID:', header, re.MULTILINE | re.IGNORECASE):
            fields[key] = 'Not specified'
            continue
        if not m or not m.group(1).strip():
            raise ValueError('Include Expert, Role and Market headers before the first timestamp.')
        fields[key] = m.group(1).strip()
        consumed.append(m.span())
    subject = re.search(r'^Core Subject:[ \t]*[^\r\n]+\r?$', header, re.MULTILINE | re.IGNORECASE)
    if subject:
        consumed.append(subject.span())
    remainder = header
    for start, end in sorted(consumed, reverse=True):
        remainder = remainder[:start] + remainder[end:]
    if remainder.strip():
        raise ValueError('Only Expert, Role and Market headers may precede the first timestamp. Add a timestamp before every utterance.')
    # Do not silently absorb a malformed timestamp as ordinary speech.
    if re.search(r'(?m)^\s*\d+:\S*\s*$', STAMP.sub('', source)):
        raise ValueError('A timestamp is invalid. Use MM:SS or HH:MM:SS.')
    passages, previous = [], -1
    for i, stamp in enumerate(stamps):
        parts = [int(n) for n in stamp.group(1).split(':')]
        if parts[-1] > 59 or (len(parts) == 3 and parts[-2] > 59):
            raise ValueError('Timestamp seconds and hour-format minutes must be below 60.')
        seconds = sum(n * 60 ** j for j, n in enumerate(reversed(parts)))
        if seconds < previous:
            raise ValueError('Keep timestamps in chronological order.')
        previous = seconds
        end = stamps[i + 1].start() if i + 1 < len(stamps) else len(source)
        block = source[stamp.end():end]
        speaker = re.match(r'\s*([^:\r\n]{1,100}):[ \t]*', block)
        if not speaker:
            raise ValueError(f'Add a speaker label after {stamp.group(1)}, for example Interviewer: or Expert:.')
        start = stamp.end() + speaker.end()
        while start < end and source[start].isspace():
            start += 1
        while end > start and source[end - 1].isspace():
            end -= 1
        if start == end:
            raise ValueError(f'The passage at {stamp.group(1)} is empty.')
        if re.search(r'(?m)^[ \t]*[^:\r\n]{1,100}:', source[start:end]):
            raise ValueError(f'Add a separate timestamp before each speaker turn after {stamp.group(1)}.')
        label = speaker.group(1).strip()
        passages.append(dict(ordinal=i, timestamp=stamp.group(1), seconds=seconds, speaker=label,
                             is_expert=label.casefold() not in {'interviewer', 'moderator', 'host'},
                             text=source[start:end], start_offset=start, end_offset=end))
    if not any(p['is_expert'] for p in passages):
        raise ValueError('Include at least one expert response.')
    return {**fields, 'passages': passages}
