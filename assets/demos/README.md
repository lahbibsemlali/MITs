# Demo recordings

Placeholder GIFs (`demo-main.gif`, `demo-search.gif`) are minimal 1×1 images so the README renders without broken links. Replace them with real screen recordings for GitHub / PyPI.

## Option A — [VHS](https://github.com/charmbracelet/vhs) (scripted GIF)

Install [VHS](https://github.com/charmbracelet/vhs), add a `demo.tape`, then:

```bash
vhs demo.tape
```

## Option B — [asciinema](https://asciinema.org/) + [agg](https://github.com/asciinema/agg)

```bash
asciinema rec demo.cast
# play with mit, exit
agg demo.cast demo-main.gif
```

## Option C — Peek / OBS

Record the terminal window and export as GIF or MP4; compress with `ffmpeg` if needed.
