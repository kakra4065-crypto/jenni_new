# update_ads_full.ps1
$AppPath = "C:\Users\Mr. Alema\Desktop\jenni_new\app.py"
$BackupPath = "$AppPath.bak"

# 1. Backup the file
Copy-Item $AppPath $BackupPath -Force
Write-Host "Backup created at $BackupPath"

# 2. Load app.py content
$content = Get-Content $AppPath -Raw

# 3. HTML overlay block with logo
$adOverlay = @"
<div id="ad-overlay">
  <video id="ad-video" style="display:none; max-width:100%;" controls autoplay playsinline></video>
  <img id="ad-image" style="display:none; max-width:100%;" alt="Ad">
  <img id="ad-logo" src="{{ url_for('static', filename='db_lotto_hall.png') }}" 
       style="position:absolute; top:20px; left:20px; width:120px; z-index:10000;">
  <div class="ad-close-hint" style="color:#fff; background:rgba(0,0,0,0.7); padding:8px; cursor:pointer;">
    Tap/click anywhere to close advert.
  </div>
</div>
<script>
  const adFiles = {{ ad_files | tojson }};
  const videoEl = document.getElementById('ad-video');
  const imgEl = document.getElementById('ad-image');
  const overlay = document.getElementById('ad-overlay');
  if (adFiles.length > 0) {
    const adFile = adFiles[Math.floor(Math.random() * adFiles.length)];
    if (adFile.endsWith('.mp4') || adFile.endsWith('.webm') || adFile.endsWith('.ogg')) {
      videoEl.src = '/static/images.advirt/' + adFile;
      videoEl.style.display = 'block';
      videoEl.onended = () => overlay.style.display = 'none';
    } else {
      imgEl.src = '/static/images.advirt/' + adFile;
      imgEl.style.display = 'block';
      overlay.onclick = () => overlay.style.display = 'none';
    }
  } else {
    overlay.style.display = 'none';
  }
</script>
"@

# 4. Pattern for inserting ad overlay
$pattern = @"
(?ms)([A-Z_]+_TEMPLATE\s*=\s*'''.*?)(</body>)
"@

$content = [regex]::Replace($content, $pattern, {
    param($m)
    if ($m.Groups[1].Value -notmatch [regex]::Escape($adOverlay)) {
        return $m.Groups[1].Value + $adOverlay + "`n</body>"
    } else {
        return $m.Value
    }
})

# 5. Add ad_files=get_ad_files() to render_template_string calls
$pattern2 = @"
(render_template_string\([^\)]*)
"@

$content = [regex]::Replace($content, $pattern2, {
    param($m)
    if ($m.Groups[1].Value -notmatch 'ad_files=') {
        return $m.Groups[1].Value.TrimEnd() + ", ad_files=get_ad_files()"
    } else {
        return $m.Value
    }
})

# 6. Save updated app.py
Set-Content $AppPath $content -Encoding UTF8
Write-Host "Ad overlay + logo injected into all templates. All render_template_string calls updated."
