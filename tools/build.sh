#!/bin/sh
# Собирает сайт для хостинга: index.html из atlas.html, robots.txt и sitemap.xml.
# Адрес сайта задаётся переменной: SITE_URL=https://ваш-домен.ru sh tools/build.sh
cd "$(dirname "$0")/.." || exit 1
SITE_URL="${SITE_URL:-https://earthatlas.ru}"
SITE_URL="$SITE_URL" python3 tools/pages.py || exit 1
TITLE="Атлас мира — интерактивная карта: страны, история, ресурсы, ветры и течения"
DESC="Интерактивная карта мира: площадь и население стран, государства прошлого с 4000 года до н. э., реки, озёра и города, месторождения ресурсов, ветры и океанские течения на карте и глобусе."
{
cat <<EOF
<!doctype html>
<html lang="ru">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover">
<title>$TITLE</title>
<meta name="description" content="$DESC">
<link rel="canonical" href="$SITE_URL/">
<link rel="icon" href="favicon.svg" type="image/svg+xml">
<link rel="icon" href="favicon.png" type="image/png" sizes="120x120">
<link rel="apple-touch-icon" href="favicon.png">
<meta name="theme-color" content="#14263a">
<meta property="og:type" content="website">
<meta property="og:locale" content="ru_RU">
<meta property="og:site_name" content="Атлас мира">
<meta property="og:title" content="Атлас мира — интерактивная карта">
<meta property="og:description" content="$DESC">
<meta property="og:url" content="$SITE_URL/">
<meta property="og:image" content="$SITE_URL/og.jpg">
<meta property="og:image:width" content="1200">
<meta property="og:image:height" content="630">
<meta name="twitter:card" content="summary_large_image">
<script type="application/ld+json">{"@context":"https://schema.org","@type":"WebApplication","name":"Атлас мира","url":"$SITE_URL/","inLanguage":"ru","applicationCategory":"EducationalApplication","operatingSystem":"Any","description":"$DESC","offers":{"@type":"Offer","price":"0","priceCurrency":"RUB"}}</script>
<style>body{margin:0}[hidden]{display:none!important}</style>
</head>
<body>
<noscript><p style="padding:16px;font:16px/1.5 sans-serif">Атлас мира — интерактивная карта: страны, история государств, реки и города, ресурсы, ветры и течения. Для работы карты включите JavaScript. Разделы: <a href="strany/">страны мира</a>, <a href="istoriya/">история государств</a>, <a href="resursy/">ресурсы</a>, <a href="vetry-i-techeniya/">ветры и течения</a>, <a href="about.html">об атласе и источниках данных</a>.</p></noscript>
EOF
grep -v '^<title>' atlas.html
printf '\n</body>\n</html>\n'
} > index.html
printf 'User-agent: *\nAllow: /\nSitemap: %s/sitemap.xml\n' "$SITE_URL" > robots.txt
D=$(date +%Y-%m-%d)
{
printf '<?xml version="1.0" encoding="UTF-8"?>\n<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
printf '<url><loc>%s/</loc><lastmod>%s</lastmod></url>\n' "$SITE_URL" "$D"
printf '<url><loc>%s/about.html</loc><lastmod>%s</lastmod></url>\n' "$SITE_URL" "$D"
[ -f tools/pages.txt ] && while read -r P; do [ -n "$P" ] && printf '<url><loc>%s/%s</loc><lastmod>%s</lastmod></url>\n' "$SITE_URL" "$P" "$D"; done < tools/pages.txt
printf '</urlset>\n'
} > sitemap.xml
echo "Собрано для $SITE_URL"
