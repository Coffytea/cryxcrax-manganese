import urllib.parse


def internal_page_shell(theme_attr, title, body_html, extra_style=""):
    return f"""<!DOCTYPE html>
<html data-theme="{theme_attr}">
<head>
<meta charset="utf-8">
<title>{title}</title>
<style>
  :root[data-theme="dark"] {{
    --bg: #1a1b1e; --panel: #202225; --text: #f5f5f6; --text-secondary: #9a9ca3;
    --border: #313338; --hover: #2a2c30; --accent: #5b8cff; --danger: #e05a5a;
  }}
  :root[data-theme="light"] {{
    --bg: #f5f5f7; --panel: #ffffff; --text: #1c1c1e; --text-secondary: #5f6368;
    --border: #e2e2e4; --hover: #f1f2f4; --accent: #3366ee; --danger: #d33a3a;
  }}
  * {{ box-sizing: border-box; }}
  html, body {{ margin: 0; padding: 0; background: var(--bg); color: var(--text);
    font-family: 'Segoe UI', -apple-system, BlinkMacSystemFont, sans-serif; }}
  .mg-page {{ max-width: 760px; margin: 0 auto; padding: 32px 24px 60px 24px; }}
  h1 {{ font-size: 22px; font-weight: 600; margin: 0 0 20px 0; }}
  .mg-card {{ background: var(--panel); border: 1px solid var(--border); border-radius: 10px;
    margin-bottom: 16px; overflow: hidden; }}
  .mg-row {{ display: flex; align-items: center; padding: 14px 18px; border-bottom: 1px solid var(--border); }}
  .mg-row:last-child {{ border-bottom: none; }}
  .mg-row:hover {{ background: var(--hover); }}
  .mg-row-label {{ flex: 1; font-size: 13.5px; }}
  .mg-row-sub {{ color: var(--text-secondary); font-size: 12px; margin-top: 2px; }}
  a {{ color: var(--accent); text-decoration: none; }}
  a:hover {{ text-decoration: underline; }}
  .mg-btn {{ display: inline-block; padding: 7px 14px; border-radius: 6px; background: var(--accent);
    color: white; font-size: 12.5px; cursor: pointer; border: none; }}
  .mg-section-title {{ font-size: 12px; text-transform: uppercase; letter-spacing: .04em;
    color: var(--text-secondary); margin: 24px 0 8px 4px; }}
  input[type=radio] {{ accent-color: var(--accent); margin-right: 10px; }}
  .mg-empty {{ padding: 40px; text-align: center; color: var(--text-secondary); }}
  {extra_style}
</style>
</head>
<body>
<div class="mg-page">
{body_html}
</div>
</body>
</html>"""


def build_settings_page(theme_attr, search_engine_name, downloads_dir, accent_color=None, new_tab_background=None, tab_suspension_enabled=True):
    engines = [
        ("Google", "google"), ("Microsoft Bing", "bing"), ("Yahoo Search", "yahoo"),
        ("DuckDuckGo", "duck"), ("Yandex", "yandex"),
    ]
    rows = ""
    for name, key in engines:
        checked = "checked" if name == search_engine_name else ""
        rows += (
            f'<label class="mg-row" style="cursor:pointer;">'
            f'<input type="radio" name="engine" {checked} '
            f'onclick="location.href=\'mangan://action?set=engine&value={key}\'">'
            f'<span class="mg-row-label">{name}</span></label>'
        )

    theme_now = "Dark" if theme_attr == "dark" else "Light"
    accent_value = accent_color or ("#5b8cff" if theme_attr == "dark" else "#3366ee")

    bg = new_tab_background or {}
    bg_type = bg.get("type")

    body = f"""
<h1>Settings</h1>
<div class="mg-section-title">Appearance</div>
<div class="mg-card">
  <div class="mg-row">
    <div>
      <div class="mg-row-label">Theme</div>
      <div class="mg-row-sub">Currently following the system setting ({theme_now}). Manganese detects Windows' light/dark preference automatically.</div>
    </div>
  </div>
  <div class="mg-row">
    <div style="flex:1;">
      <div class="mg-row-label">Accent color</div>
      <div class="mg-row-sub">Used for tab highlights, buttons, and links throughout Manganese.</div>
    </div>
    <input type="color" value="{accent_value}"
      style="width:40px;height:28px;border:none;border-radius:6px;background:none;cursor:pointer;padding:0;"
      onchange="location.href='mangan://action?set=accent&value=' + encodeURIComponent(this.value)">
  </div>
  <a class="mg-row" style="text-decoration:none;color:inherit;" href="mangan://action?set=accent&value={urllib.parse.quote(('#5b8cff' if theme_attr == 'dark' else '#3366ee'), safe='')}">
    <span class="mg-row-label" style="color:var(--text-secondary);font-size:12px;">Reset to default</span>
  </a>
</div>
<div class="mg-section-title">New Tab page</div>
<div class="mg-card">
  <label class="mg-row" style="cursor:pointer;">
    <input type="radio" name="ntbg" {"checked" if bg_type is None else ""}
      onclick="location.href='mangan://action?clear_newtab_bg=1'">
    <span class="mg-row-label">Default</span>
  </label>
  <label class="mg-row" style="cursor:pointer;">
    <input type="radio" name="ntbg" {"checked" if bg_type == "color" else ""}
      onclick="location.href='mangan://action?set=newtab_bg&value=' + encodeURIComponent(document.getElementById('ntbgColorPicker').value)">
    <span class="mg-row-label" style="flex:1;">Solid color</span>
    <input type="color" id="ntbgColorPicker" value="{bg.get('value') if bg_type == 'color' else '#5b8cff'}"
      style="width:32px;height:24px;border:none;border-radius:6px;background:none;cursor:pointer;padding:0;"
      onchange="location.href='mangan://action?set=newtab_bg&value=' + encodeURIComponent(this.value)">
  </label>
  <label class="mg-row" style="cursor:pointer;">
    <input type="radio" name="ntbg" {"checked" if bg_type == "image" else ""}
      onclick="location.href='mangan://action?choose_newtab_image=1'">
    <span class="mg-row-label">Custom image&hellip;</span>
  </label>
</div>
<div class="mg-section-title">Search engine</div>
<div class="mg-card">
  {rows}
</div>
<div class="mg-section-title">Performance</div>
<div class="mg-card">
  <label class="mg-row" style="cursor:pointer;">
    <input type="checkbox" {"checked" if tab_suspension_enabled else ""}
      onclick="location.href='mangan://action?set=tab_suspension&value=' + (this.checked ? '1' : '0')"
      style="margin-right:10px;">
    <div style="flex:1;">
      <div class="mg-row-label">Free up memory from inactive tabs</div>
      <div class="mg-row-sub">Unloads tabs you haven't used in a while and reloads them when you switch back, similar to Chrome's memory saver.</div>
    </div>
  </label>
</div>
<div class="mg-section-title">Downloads</div>
<div class="mg-card">
  <div class="mg-row">
    <div class="mg-row-label">Location</div>
    <div class="mg-row-sub">{downloads_dir}</div>
  </div>
  <a class="mg-row" style="text-decoration:none;color:inherit;" href="mangan://downloads">
    <span class="mg-row-label">Downloads history</span><span>&rsaquo;</span>
  </a>
</div>
<div class="mg-section-title">Privacy and security</div>
<div class="mg-card">
  <a class="mg-row" style="text-decoration:none;color:inherit;" href="mangan://history">
    <span class="mg-row-label">History</span><span>&rsaquo;</span>
  </a>
  <a class="mg-row" style="text-decoration:none;color:inherit;" href="mangan://sitedata">
    <span class="mg-row-label">Cookies and site data</span><span>&rsaquo;</span>
  </a>
</div>
<div class="mg-section-title">About</div>
<div class="mg-card">
  <div class="mg-row"><span class="mg-row-label">Manganese</span><span class="mg-row-sub">Cryxcrax Manganese V2.0 &middot; Built by Mult1c</span></div>
</div>
"""
    return internal_page_shell(theme_attr, "Settings", body)


def build_downloads_page(theme_attr, downloads_list, human_size):
    if not downloads_list:
        body = '<h1>Downloads</h1><div class="mg-card"><div class="mg-empty">No downloads yet</div></div>'
        return internal_page_shell(theme_attr, "Downloads", body)

    rows = ""
    for dl in reversed(downloads_list):
        status = "Done" if dl.is_finished else f"{human_size(dl.received_bytes)} / {human_size(dl.total_bytes)}"
        when = dl.started_at.toString("MMM d, yyyy \u2022 h:mm AP") if hasattr(dl, "started_at") else ""
        rows += f"""
<div class="mg-row">
  <div style="flex:1;">
    <div class="mg-row-label">{dl.filename}</div>
    <div class="mg-row-sub">{status} &middot; {when}</div>
  </div>
</div>"""
    body = f'<h1>Downloads</h1><div class="mg-card">{rows}</div>'
    return internal_page_shell(theme_attr, "Downloads", body)


def build_history_page(theme_attr, history_entries):
    if not history_entries:
        body = ('<h1>History</h1>'
                '<div class="mg-card"><div class="mg-empty">No browsing history yet</div></div>')
        return internal_page_shell(theme_attr, "History", body)

    groups = {}
    order = []
    for entry in reversed(history_entries):
        day = entry["dt"].date().toString("dddd, MMMM d, yyyy")
        if day not in groups:
            groups[day] = []
            order.append(day)
        groups[day].append(entry)

    sections = ""
    for day in order:
        rows = ""
        for entry in groups[day]:
            time_str = entry["dt"].time().toString("h:mm AP")
            safe_title = (entry["title"] or entry["url"]).replace("<", "&lt;")
            visited_at = entry["dt"].toString("yyyy-MM-ddTHH:mm:ss")
            delete_href = (
                f"mangan://action?delete_history_entry=1"
                f"&url={urllib.parse.quote(entry['url'], safe='')}"
                f"&visited_at={urllib.parse.quote(visited_at, safe='')}"
            )
            rows += f"""
<div class="mg-row" style="gap:10px;">
  <a href="{entry['url']}" style="text-decoration:none;color:inherit;display:flex;flex:1;min-width:0;align-items:center;gap:10px;">
    <div style="width:64px;flex-shrink:0;color:var(--text-secondary);font-size:12px;">{time_str}</div>
    <div style="flex:1;overflow:hidden;text-overflow:ellipsis;white-space:nowrap;">{safe_title}</div>
  </a>
  <a href="{delete_href}" title="Remove from history" style="flex-shrink:0;color:var(--text-secondary);text-decoration:none;font-size:16px;padding:2px 6px;">&times;</a>
</div>"""
        sections += f'<div class="mg-section-title">{day}</div><div class="mg-card">{rows}</div>'

    body = f"""
<h1>History</h1>
<div class="mg-card">
  <a class="mg-row" style="text-decoration:none;color:var(--danger);justify-content:center;font-weight:500;" href="mangan://action?clear_history=1">
    Delete browsing history
  </a>
</div>
{sections}
"""
    return internal_page_shell(theme_attr, "History", body)


def build_site_data_page(theme_attr, sites):
    header = """
<h1>Site data</h1>
<div class="mg-card">
  <a class="mg-row" style="text-decoration:none;color:var(--danger);justify-content:center;font-weight:500;" href="mangan://action?clear_all_cookies=1">
    Clear all cookies and site data
  </a>
</div>
"""
    if not sites:
        body = header + '<div class="mg-card"><div class="mg-empty">No sites have stored cookies</div></div>'
        return internal_page_shell(theme_attr, "Site data", body)

    rows = ""
    for domain, count in sites:
        cookie_word = "cookie" if count == 1 else "cookies"
        delete_href = f"mangan://action?delete_site_cookies=1&domain={urllib.parse.quote(domain, safe='')}"
        rows += f"""
<div class="mg-row" style="gap:10px;">
  <div style="flex:1;min-width:0;">
    <div class="mg-row-label">{domain}</div>
    <div class="mg-row-sub">{count} {cookie_word}</div>
  </div>
  <a href="{delete_href}" title="Remove site data" style="flex-shrink:0;color:var(--text-secondary);text-decoration:none;font-size:16px;padding:2px 6px;">&times;</a>
</div>"""
    body = header + f'<div class="mg-section-title">{len(sites)} sites</div><div class="mg-card">{rows}</div>'
    return internal_page_shell(theme_attr, "Site data", body)
