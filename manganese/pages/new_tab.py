import json

_NEW_TAB_TEMPLATE = """<!DOCTYPE html>
<html data-theme="__THEME__">
<head>
<meta charset="utf-8">
<title>New Tab</title>

<!-- Import Syne font from Google Fonts -->
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Syne:wght@600&display=swap" rel="stylesheet">

<style>
  :root[data-theme="dark"] {
    --bg: #1a1b1e;
    --text: #f5f5f6;
    --text-secondary: #9a9ca3;
    --search-bg: #2a2c30;
    --search-border: #3a3c42;
    --search-border-focus: #5b8cff;
    --search-placeholder: #7a7c82;
    --accent: #5b8cff;
    --tile-bg: #202225;
    --tile-hover: #2a2c30;
    --tile-text: #c7c8cc;
    --divider: #313338;
    --shadow: rgba(0,0,0,0.35);
  }
  :root[data-theme="light"] {
    --bg: #f5f5f7;
    --text: #1c1c1e;
    --text-secondary: #5f6368;
    --search-bg: #ffffff;
    --search-border: #c9cad0;
    --search-border-focus: #3366ee;
    --search-placeholder: #9a9ba1;
    --accent: #3366ee;
    --tile-bg: #ffffff;
    --tile-hover: #e9e9ec;
    --tile-text: #3c3c43;
    --divider: #e2e2e4;
    --shadow: rgba(60,60,67,0.18);
  }
  * { box-sizing: border-box; }
  html, body {
    margin: 0; padding: 0; height: 100%;
    color: var(--text);
  }
  html {
    /* html keeps the plain theme color so there's never a flash of
       unstyled/black background before #mgBackdrop's own script runs. */
    background: var(--bg);
  }
  body {
    /* Deliberately transparent, not var(--bg) -- body covers the same
       full-viewport area #mgBackdrop does, and an opaque body background
       painted on top of #mgBackdrop's negative z-index layer is what
       caused a custom background to flash briefly then disappear: body's
       own solid color was winning the paint order a moment after
       #mgBackdrop's script set the image/color. Making body transparent
       lets #mgBackdrop (and, through it, html's plain fallback) be the
       only thing actually painting a background color. */
    background: transparent;
  }
  #mgBackdrop {
    position: fixed;
    inset: 0;
    z-index: -2;
    background-size: cover;
    background-position: center;
    background-repeat: no-repeat;
    transition: background-color .2s ease;
  }
  /* Subtle scrim so text/search bar stay readable over a busy custom
     background image -- only applied when an image background is set
     (toggled via the has-image class from __mgSetBackground below). */
  #mgBackdrop.has-image::after {
    content: "";
    position: absolute;
    inset: 0;
    background: var(--bg);
    opacity: .38;
  }
  body {
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif;
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    -webkit-user-select: none;
    user-select: none;
    animation: mgFadeIn .25s ease;
  }
  @keyframes mgFadeIn { from { opacity: 0; } to { opacity: 1; } }
  .mg-clock {
    position: fixed;
    top: 22px;
    right: 28px;
    text-align: right;
    color: var(--text-secondary);
    font-size: 13px;
    padding: 6px 12px;
    border-radius: 999px;
    transition: background-color .15s ease, color .15s ease, box-shadow .15s ease;
  }
  /* Applied by __mgUpdateClockContrast below when the clock's default
     text color wouldn't have enough contrast against the current
     background (a busy custom image, or a background color close to the
     text color) -- gives it a small frosted pill to sit in instead of
     just disappearing into the background. */
  .mg-clock.mg-clock-floating {
    background: rgba(20, 20, 22, 0.55);
    color: #ffffff;
    box-shadow: 0 2px 12px rgba(0,0,0,0.25);
    backdrop-filter: blur(6px);
  }
  .mg-clock.mg-clock-floating.mg-clock-floating-light {
    background: rgba(255, 255, 255, 0.72);
    color: #1c1c1e;
  }
  .mg-logo {
    font-family: 'Syne', sans-serif; /* Applied Syne font here */
    font-size: 40px;
    font-weight: 600;
    letter-spacing: -0.5px;
    margin-bottom: 34px;
    color: var(--text);
    display: flex;
    align-items: baseline;
  }
  .mg-logo .dot { color: var(--accent); margin-left: 2px; }
  .mg-search-wrap {
    position: relative;
    width: 560px;
    max-width: 88vw;
  }
  .mg-search-icon {
    position: absolute;
    left: 18px;
    top: 50%;
    transform: translateY(-50%);
    width: 18px; height: 18px;
    display: flex;
  }
  #mgSearchInput {
    width: 100%;
    height: 48px;
    border-radius: 24px;
    border: 1px solid var(--search-border);
    background: var(--search-bg);
    color: var(--text);
    font-size: 15px;
    padding: 0 20px 0 48px;
    outline: none;
    transition: border-color .15s ease, box-shadow .15s ease;
  }
  #mgSearchInput::placeholder { color: var(--search-placeholder); }
  #mgSearchInput:focus {
    border-color: var(--search-border-focus);
    box-shadow: 0 2px 10px var(--shadow);
  }
  /* Custom accent color override (Settings > Appearance) -- !important so
     it reliably wins over the per-theme :root[data-theme] defaults above,
     which have identical selector specificity (both target the root
     element) and would otherwise depend on source order alone, which is
     fragile if this block is ever reordered. */
  html {
    --accent: __ACCENT_COLOR__ !important;
    --search-border-focus: __ACCENT_COLOR__ !important;
  }
</style>
</head>
<body>
  <div id="mgBackdrop"></div>
  <div class="mg-clock" id="mgClock"></div>
  <div class="mg-logo">Manganese<span class="dot"></span></div>
  <div class="mg-search-wrap">
    <span class="mg-search-icon">
      <svg viewBox="0 0 24 24" width="18" height="18" xmlns="http://www.w3.org/2000/svg">
        <circle cx="11" cy="11" r="7" fill="none" stroke="var(--search-placeholder)" stroke-width="2"/>
        <line x1="16.2" y1="16.2" x2="21" y2="21" stroke="var(--search-placeholder)" stroke-width="2" stroke-linecap="round"/>
      </svg>
    </span>
    <input id="mgSearchInput" type="text" placeholder="Search" autofocus autocomplete="off" spellcheck="false">
  </div>

<script>
  window.__mgSearchPrefix = __SEARCH_PREFIX__;

  // Decides whether the clock needs its floating pill background, by
  // sampling the *actual visible pixels* behind it -- not just guessing
  // from the background type. For a solid color this is instant (read the
  // color, compute luminance). For an image, the relevant region of the
  // image is drawn to an offscreen canvas and its real average brightness
  // is measured, so a light patch in a mostly-dark photo (or vice versa)
  // is detected correctly instead of just assuming "image = risky".
  function __mgRelativeLuminance(r, g, b) {
    // Standard WCAG relative luminance formula.
    function chan(c) {
      c = c / 255;
      return c <= 0.03928 ? c / 12.92 : Math.pow((c + 0.055) / 1.055, 2.4);
    }
    return 0.2126 * chan(r) + 0.7152 * chan(g) + 0.0722 * chan(b);
  }

  function __mgHexToRgb(hex) {
    var m = /^#?([a-f\\d]{2})([a-f\\d]{2})([a-f\\d]{2})/i.exec(hex);
    if (!m) return null;
    return [parseInt(m[1], 16), parseInt(m[2], 16), parseInt(m[3], 16)];
  }

  function __mgApplyClockStyle(luminance) {
    var clock = document.getElementById('mgClock');
    if (!clock || luminance === null) return;
    // Text sits on --text-secondary, which already has enough contrast
    // against the *plain* theme background by design -- only override
    // when a custom background pushes luminance into a range where the
    // default text color would actually struggle (roughly: light text on
    // a light background, or the reverse extreme).
    var htmlIsDark = document.documentElement.getAttribute('data-theme') === 'dark';
    var defaultTextIsLight = htmlIsDark; // dark theme uses light text
    var backgroundIsLight = luminance > 0.5;
    var poorContrast = (defaultTextIsLight && backgroundIsLight) || (!defaultTextIsLight && !backgroundIsLight);
    clock.classList.toggle('mg-clock-floating', poorContrast);
    clock.classList.toggle('mg-clock-floating-light', poorContrast && backgroundIsLight);
  }

  function __mgUpdateClockContrast(spec) {
    var clock = document.getElementById('mgClock');
    if (!clock) return;
    if (!spec || !spec.value) {
      // Plain theme background -- the default text color is already
      // designed for it, so no pill needed.
      clock.classList.remove('mg-clock-floating', 'mg-clock-floating-light');
      return;
    }
    if (spec.type === 'color') {
      var rgb = __mgHexToRgb(spec.value);
      if (rgb) __mgApplyClockStyle(__mgRelativeLuminance(rgb[0], rgb[1], rgb[2]));
      return;
    }
    if (spec.type === 'image') {
      // Sample a small canvas covering roughly the clock's on-screen area
      // (top-right corner) rather than the whole image, since that's the
      // only region that actually matters for this decision.
      var img = new Image();
      img.onload = function () {
        try {
          var canvas = document.createElement('canvas');
          var sw = 40, sh = 40;
          canvas.width = sw;
          canvas.height = sh;
          var ctx = canvas.getContext('2d');
          // Draw the image as it's actually displayed (background-size:
          // cover, background-position: center) and read pixels from the
          // top-right corner where the clock sits.
          var scale = Math.max(window.innerWidth / img.width, window.innerHeight / img.height);
          var dw = img.width * scale, dh = img.height * scale;
          var dx = (window.innerWidth - dw) / 2;
          var dy = (window.innerHeight - dh) / 2;
          // Sample region: top-right ~180x60 screen px, mapped into the
          // full drawn-image coordinate space, then rendered at reduced
          // size into our small canvas for cheap averaging.
          ctx.drawImage(img, -dx, -dy, dw, dh, -(window.innerWidth - sw - 28) , -22, dw * (sw / window.innerWidth), dh * (sh / window.innerHeight));
          var data = ctx.getImageData(0, 0, sw, sh).data;
          var total = 0, count = 0;
          for (var i = 0; i < data.length; i += 4) {
            total += __mgRelativeLuminance(data[i], data[i + 1], data[i + 2]);
            count++;
          }
          __mgApplyClockStyle(count ? total / count : null);
        } catch (e) {
          // Canvas can throw on tainted/cross-origin data in edge cases --
          // fall back to the pill unconditionally rather than leaving the
          // clock unreadable.
          __mgApplyClockStyle(0.5);
        }
      };
      img.onerror = function () { __mgApplyClockStyle(null); };
      img.src = spec.value;
    }
  }

  // Applies (or clears) a custom New Tab background. `spec` is either
  // null/undefined (use the plain theme background), {type:"color",
  // value:"#rrggbb"}, or {type:"image", value:"<data: URI>"} -- images are
  // always passed in as data: URIs (converted in Python, see
  // TabbedBrowser._new_tab_background_css) since this page has no access
  // to arbitrary local file:// paths from its manganese:// origin.
  window.__mgSetBackground = function(spec) {
    var el = document.getElementById('mgBackdrop');
    if (!el) return;
    if (!spec || !spec.value) {
      el.style.backgroundImage = '';
      el.style.backgroundColor = '';
      el.classList.remove('has-image');
      __mgUpdateClockContrast(null);
      return;
    }
    if (spec.type === 'image') {
      el.style.backgroundColor = '';
      // Keep the quotes JSON.stringify produces -- url("...") with a
      // properly quoted, escaped string is valid CSS and safe for any
      // data: URI content. Stripping the quotes (previous version) built
      // an unquoted url(...) that could fail to parse depending on the
      // exact bytes in the base64 payload, which silently dropped the
      // background back to nothing after a first successful paint.
      el.style.backgroundImage = 'url(' + JSON.stringify(spec.value) + ')';
      el.classList.add('has-image');
    } else {
      el.style.backgroundImage = '';
      el.style.backgroundColor = spec.value;
      el.classList.remove('has-image');
    }
    __mgUpdateClockContrast(spec);
  };
  window.__mgSetBackground(__NEW_TAB_BACKGROUND__);

  function __mgSubmit() {
    var val = document.getElementById('mgSearchInput').value.trim();
    if (!val) return;
    var target;
    if (/^https?:\\/\\//i.test(val)) {
      target = val;
    } else if (val.indexOf(' ') === -1 && val.indexOf('.') !== -1) {
      target = 'https://' + val;
    } else {
      target = window.__mgSearchPrefix + encodeURIComponent(val);
    }
    window.location.href = target;
  }

  document.getElementById('mgSearchInput').addEventListener('keydown', function (e) {
    if (e.key === 'Enter') { __mgSubmit(); }
  });

  function __mgUpdateClock() {
    var el = document.getElementById('mgClock');
    if (!el) return;
    var now = new Date();
    var h = now.getHours(), m = now.getMinutes();
    var hh = (h % 12 === 0) ? 12 : (h % 12);
    var mm = (m < 10 ? '0' : '') + m;
    var ampm = h >= 12 ? 'PM' : 'AM';
    el.textContent = hh + ':' + mm + ' ' + ampm;
  }
  __mgUpdateClock();
  setInterval(__mgUpdateClock, 15000);
</script>
</body>
</html>
"""


def background_to_data_uri(background):
    import base64
    import mimetypes
    import os

    if not background or background.get("type") != "image":
        return background
    path = background.get("value") or ""
    if not path or not os.path.isfile(path):
        return None
    mime, _ = mimetypes.guess_type(path)
    if not mime or not mime.startswith("image/"):
        mime = "image/png"
    try:
        with open(path, "rb") as f:
            data = f.read()
    except Exception:
        return None
    if len(data) > 8 * 1024 * 1024:
        return None
    encoded = base64.b64encode(data).decode("ascii")
    return {"type": "image", "value": f"data:{mime};base64,{encoded}"}


def new_tab_html(dark_mode, search_prefix, background=None, accent_color=None):
    theme_attr = "dark" if dark_mode else "light"
    search_prefix_json = json.dumps(search_prefix)
    background_json = json.dumps(background_to_data_uri(background))
    default_accent = "#5b8cff" if dark_mode else "#3366ee"
    accent = accent_color or default_accent

    html = _NEW_TAB_TEMPLATE
    html = html.replace("__THEME__", theme_attr)
    html = html.replace("__SEARCH_PREFIX__", search_prefix_json)
    html = html.replace("__NEW_TAB_BACKGROUND__", background_json)
    html = html.replace("__ACCENT_COLOR__", accent)
    return html
