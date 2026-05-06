// This work is licensed under a Attribution-NonCommercial-ShareAlike 4.0 International (CC BY-NC-SA 4.0)
// https://creativecommons.org/licenses/by-nc-sa/4.0/
// © MEOW PURR
// Telegram: @MeowForex1
//@version=6
indicator("Breakout System", shorttitle="Breakout", overlay=true, max_bars_back=500, max_labels_count=500)
//--------------------------------------------------------------------------------------------------
// Inputs
//--------------------------------------------------------------------------------------------------
groupAlpha = "Vector Mesh"
groupBeta = "Echo Cluster"
groupGamma = "Phase Gate"
groupDash = "Console Grid"
waveDepth = input.int(5, "Node Span", minval=1, maxval=10, group=groupAlpha)
adaptiveMode = input.bool(true, "Adaptive Bias", group=groupAlpha)
cycleMode = input.string("MT", "Cycle Lane", options=["ST", "MT", "LT"], group=groupBeta)
proximityFactor = input.int(5, "Cluster Count", minval=1, maxval=20, group=groupBeta)
echoThreshold = input.float(0.60, "Echo Floor", minval=0.0, maxval=1.0, step=0.05, group=groupBeta)
pulseQuality = input.float(0.50, "Pulse Score", minval=0.0, maxval=1.0, step=0.05, group=groupBeta)
harmonicGate = input.float(0.65, "Phase Limit", minval=0.0, maxval=1.0, step=0.05, group=groupBeta)
expansionBuffer = input.float(0.2, "Drift Buffer", minval=0.0, group=groupGamma)
flowMultiplier = input.float(1.1, "Flux Multiplier", minval=0.5, group=groupGamma)
restPeriod = input.int(10, "Reset Gap", minval=0, group=groupGamma)
showDashboard = input.bool(true, "Show Console", group=groupDash)
dashPosition = input.string("Top Right", "Console Position", options=["Top Right", "Top Left", "Bottom Right", "Bottom Left"], group=groupDash)
//--------------------------------------------------------------------------------------------------
// Session Clock
//--------------------------------------------------------------------------------------------------
sydHour = hour(time, "Australia/Sydney")
sydMin = minute(time, "Australia/Sydney")
tokHour = hour(time, "Asia/Tokyo")
tokMin = minute(time, "Asia/Tokyo")
lonHour = hour(time, "Europe/London")
lonMin = minute(time, "Europe/London")
nyHour = hour(time, "America/New_York")
nyMin = minute(time, "America/New_York")
inSydney = sydHour >= 7 and sydHour < 16
inTokyo = tokHour >= 9 and tokHour < 18
inLondon = lonHour >= 8 and lonHour < 17
inNewYork = nyHour >= 8 and nyHour < 17
f_minutes_left(int endHour, int h, int m) =>
math.max((endHour - h) * 60 - m, 0)
sydneyRemaining = inSydney ? f_minutes_left(16, sydHour, sydMin) : 0
tokyoRemaining = inTokyo ? f_minutes_left(18, tokHour, tokMin) : 0
londonRemaining = inLondon ? f_minutes_left(17, lonHour, lonMin) : 0
newYorkRemaining = inNewYork ? f_minutes_left(17, nyHour, nyMin) : 0
f_format_time(int totalMins) =>
int hrs = int(math.floor(totalMins / 60))
int mins = totalMins % 60
hrs > 0 ? str.tostring(hrs) + "h " + str.tostring(mins) + "m" : str.tostring(mins) + "m"
f_current_session() =>
string sess = "Off-Hours"
if inLondon and inNewYork
sess := "London/NY"
else if inTokyo and inLondon
sess := "Tokyo/London"
else if inSydney and inTokyo
sess := "Sydney/Tokyo"
else if inNewYork
sess := "New York"
else if inLondon
sess := "London"
else if inTokyo
sess := "Tokyo"
else if inSydney
sess := "Sydney"
sess
currentSession = f_current_session()
//--------------------------------------------------------------------------------------------------
// Types
//--------------------------------------------------------------------------------------------------
type StructurePoint
float price
int index
string term
float feat1
float feat2
float score
//--------------------------------------------------------------------------------------------------
// Helpers
//--------------------------------------------------------------------------------------------------
f_clamp01(float x) =>
math.max(0.0, math.min(1.0, x))
f_getDistance(StructurePoint p1, StructurePoint p2) =>
math.abs(p1.feat1 - p2.feat1) + math.abs(p1.feat2 - p2.feat2) + math.abs(p1.score - p2.score) * 0.5
f_detect_pivots(int len) =>
ph = ta.pivothigh(high, len, len)
pl = ta.pivotlow(low, len, len)
[ph, pl]
f_knn_score(StructurePoint current, array<StructurePoint> history, int k) =>
float outScore = 0.5
int n = array.size(history)
if n > 0
int safeK = math.min(k, n)
array<float> distances = array.new_float(0)
for i = 0 to n - 1
dist = f_getDistance(current, array.get(history, i))
array.push(distances, dist)
array<int> sortedIndices = array.sort_indices(distances)
float sumScore = 0.0
for i = 0 to safeK - 1
idx = array.get(sortedIndices, i)
neighbor = array.get(history, idx)
sumScore += neighbor.score
outScore := sumScore / safeK
outScore
//--------------------------------------------------------------------------------------------------
// Core Math
//--------------------------------------------------------------------------------------------------
atr200 = ta.atr(200)
avgAtr200 = ta.sma(atr200, 200)
volatilityRatio = atr200 / nz(avgAtr200, atr200)
smoothedRatio = ta.ema(volatilityRatio, 50)
dynamicMultiplier = adaptiveMode ? math.pow(nz(smoothedRatio, 1.0), 1.5) : 1.0
baseLen = math.max(3, int(math.round((11 - waveDepth) * dynamicMultiplier)))
mtLen = baseLen * 3
ltLen = mtLen * 3
atr14 = ta.atr(14)
atrMA100 = ta.sma(atr14, 100)
relATR = atr14 / nz(atrMA100, atr14)
volMA100 = ta.sma(volume, 100)
relVol = volume / nz(volMA100, volume)
fastEMA = ta.ema(close, 21)
slowEMA = ta.ema(close, 55)
trendBull = close > fastEMA and fastEMA > slowEMA
trendBear = close < fastEMA and fastEMA < slowEMA
//--------------------------------------------------------------------------------------------------
// Pivot Quality
//--------------------------------------------------------------------------------------------------
f_quality_high_safe(float ph, int len, float rVol, float rAtr) =>
float lowestInRange = low[1]
for i = 1 to len
val = low[i]
if val < lowestInRange
lowestInRange := val
reaction = ph - lowestInRange
reactionScore = f_clamp01(reaction / (atr14 * 2))
volScore = f_clamp01(rVol / 2.0)
atrScore = f_clamp01(rAtr / 2.0)
0.50 * reactionScore + 0.30 * volScore + 0.20 * atrScore
f_quality_low_safe(float pl, int len, float rVol, float rAtr) =>
float highestInRange = high[1]
for i = 1 to len
val = high[i]
if val > highestInRange
highestInRange := val
reaction = highestInRange - pl
reactionScore = f_clamp01(reaction / (atr14 * 2))
volScore = f_clamp01(rVol / 2.0)
atrScore = f_clamp01(rAtr / 2.0)
0.50 * reactionScore + 0.30 * volScore + 0.20 * atrScore
//--------------------------------------------------------------------------------------------------
// Structure Engine
//--------------------------------------------------------------------------------------------------
var array<StructurePoint> stHistH = array.new<StructurePoint>()
var array<StructurePoint> stHistL = array.new<StructurePoint>()
var array<StructurePoint> mtHistH = array.new<StructurePoint>()
var array<StructurePoint> mtHistL = array.new<StructurePoint>()
var array<StructurePoint> ltHistH = array.new<StructurePoint>()
var array<StructurePoint> ltHistL = array.new<StructurePoint>()
var float actSTRes = na
var float actSTSup = na
var float actMTRes = na
var float actMTSup = na
var float actLTRes = na
var float actLTSup = na
var float actSTResC = na
var float actSTSupC = na
var float actMTResC = na
var float actMTSupC = na
var float actLTResC = na
var float actLTSupC = na
f_process_term(float ph, float pl, int len, string term, array<StructurePoint> hH, array<StructurePoint> hL) =>
float vRes = na
float vSup = na
float cRes = na
float cSup = na
float cVol = nz(relVol[len], 1.0)
float cAtr = nz(relATR[len], 1.0)
if not na(ph)
qH = f_quality_high_safe(ph, len, cVol, cAtr)
pH = StructurePoint.new(ph, bar_index[len], term, cAtr, cVol, qH)
knnValH = f_knn_score(pH, hH, proximityFactor)
finalScoreH = 0.6 * knnValH + 0.4 * qH
if finalScoreH >= echoThreshold and qH >= pulseQuality
vRes := ph
cRes := finalScoreH
array.push(hH, pH)
if array.size(hH) > 100
array.shift(hH)
if not na(pl)
qL = f_quality_low_safe(pl, len, cVol, cAtr)
pL = StructurePoint.new(pl, bar_index[len], term, cAtr, cVol, qL)
knnValL = f_knn_score(pL, hL, proximityFactor)
finalScoreL = 0.6 * knnValL + 0.4 * qL
if finalScoreL >= echoThreshold and qL >= pulseQuality
vSup := pl
cSup := finalScoreL
array.push(hL, pL)
if array.size(hL) > 100
array.shift(hL)
[vRes, vSup, cRes, cSup]
[stPH, stPL] = f_detect_pivots(baseLen)
[stR, stS, stRC, stSC] = f_process_term(stPH, stPL, baseLen, "ST", stHistH, stHistL)
[mtPH, mtPL] = f_detect_pivots(mtLen)
[mtR, mtS, mtRC, mtSC] = f_process_term(mtPH, mtPL, mtLen, "MT", mtHistH, mtHistL)
[ltPH, ltPL] = f_detect_pivots(ltLen)
[ltR, ltS, ltRC, ltSC] = f_process_term(ltPH, ltPL, ltLen, "LT", ltHistH, ltHistL)
if not na(stR)
actSTRes := stR
actSTResC := stRC
if not na(stS)
actSTSup := stS
actSTSupC := stSC
if not na(mtR)
actMTRes := mtR
actMTResC := mtRC
if not na(mtS)
actMTSup := mtS
actMTSupC := mtSC
if not na(ltR)
actLTRes := ltR
actLTResC := ltRC
if not na(ltS)
actLTSup := ltS
actLTSupC := ltSC
//--------------------------------------------------------------------------------------------------
// Raw Signal Logic
//--------------------------------------------------------------------------------------------------
float sRes = na
float sSup = na
float sResC = na
float sSupC = na
if cycleMode == "ST"
sRes := actSTRes
sSup := actSTSup
sResC := actSTResC
sSupC := actSTSupC
else if cycleMode == "MT"
sRes := actMTRes
sSup := actMTSup
sResC := actMTResC
sSupC := actMTSupC
else
sRes := actLTRes
sSup := actLTSup
sResC := actLTResC
sSupC := actLTSupC
breakUp = not na(sRes) and close > sRes + atr14 * expansionBuffer and close[1] <= sRes
breakDn = not na(sSup) and close < sSup - atr14 * expansionBuffer and close[1] >= sSup
volMA20 = ta.sma(volume, 20)
volOk = (volume / nz(volMA20, volume)) > flowMultiplier
var int lastSigBar = 0
cooldownOk = (bar_index - lastSigBar) > restPeriod
float buyStrength = 0.0
if breakUp
buyStrength := 0.4 * nz(sResC, 0.5) + 0.3 * (trendBull ? 1.0 : 0.0) + 0.3 * (volOk ? 1.0 : 0.5)
float sellStrength = 0.0
if breakDn
sellStrength := 0.4 * nz(sSupC, 0.5) + 0.3 * (trendBear ? 1.0 : 0.0) + 0.3 * (volOk ? 1.0 : 0.5)
rawBuy = breakUp and cooldownOk and buyStrength >= harmonicGate
rawSell = breakDn and cooldownOk and sellStrength >= harmonicGate
//--------------------------------------------------------------------------------------------------
// Alternating Logic
//--------------------------------------------------------------------------------------------------
var int direction = 0
bool finalBuy = false
bool finalSell = false
if barstate.isconfirmed
if rawBuy and rawSell
if buyStrength > sellStrength
rawSell := false
else
rawBuy := false
if rawBuy and direction != 1
finalBuy := true
direction := 1
lastSigBar := bar_index
if cycleMode == "ST"
actSTRes := na
else if cycleMode == "MT"
actMTRes := na
else
actLTRes := na
if rawSell and direction != -1
finalSell := true
direction := -1
lastSigBar := bar_index
if cycleMode == "ST"
actSTSup := na
else if cycleMode == "MT"
actMTSup := na
else
actLTSup := na
//--------------------------------------------------------------------------------------------------
// Colors
//--------------------------------------------------------------------------------------------------
bgColor = color.rgb(12, 14, 20)
headerBg = color.rgb(28, 32, 44)
borderColor = color.rgb(78, 84, 110)
textColor = color.rgb(220, 220, 230)
labelColor = color.rgb(160, 165, 185)
buyColor = color.lime
sellColor = color.rgb(255, 105, 180)
waitColor = color.rgb(255, 193, 7)
sessionColor = color.rgb(255, 200, 100)
activeSessionColor = color.rgb(0, 230, 119)
inactiveSessionColor = color.rgb(115, 115, 135)
authorColor = color.rgb(255, 215, 0)
//--------------------------------------------------------------------------------------------------
// Dashboard Memory
//--------------------------------------------------------------------------------------------------
var string currentSignal = "WAITING"
var float entryPrice = na
var int signalBar = na
if finalBuy
currentSignal := "BUY"
entryPrice := close
signalBar := bar_index
if finalSell
currentSignal := "SELL"
entryPrice := close
signalBar := bar_index
//--------------------------------------------------------------------------------------------------
// CAT SIGNALS
//--------------------------------------------------------------------------------------------------
var int lastBuyCatBar = na
var int lastSellCatBar = na
if finalBuy and barstate.isconfirmed and (na(lastBuyCatBar) or lastBuyCatBar != bar_index)
label.new(
bar_index,
na,
" ",
xloc=xloc.bar_index,
yloc=yloc.belowbar,
style=label.style_none,
textcolor=buyColor,
size=size.huge)
lastBuyCatBar := bar_index
if finalSell and barstate.isconfirmed and (na(lastSellCatBar) or lastSellCatBar != bar_index)
label.new(
bar_index,
na,
" ",
xloc=xloc.bar_index,
yloc=yloc.abovebar,
style=label.style_none,
textcolor=sellColor,
size=size.huge)
lastSellCatBar := bar_index
//--------------------------------------------------------------------------------------------------
// Dashboard
//--------------------------------------------------------------------------------------------------
var table dashTable = na
if showDashboard and barstate.islast
tablePos = switch dashPosition
"Top Right" => position.top_right
"Top Left" => position.top_left
"Bottom Right" => position.bottom_right
"Bottom Left" => position.bottom_left
=> position.top_right
if not na(dashTable)
table.delete(dashTable)
dashTable := table.new(tablePos, 2, 14, bgcolor=bgColor, border_width=2, border_color=borderColor, frame_width=3, frame_color=borderColor)
table.cell(dashTable, 0, 0, " BREAKOUT SYSTEM", text_color=color.rgb(100, 180, 255), text_size=size.normal, bgcolor=headerBg, text_halign=text.align_center)
table.merge_cells(dashTable, 0, 0, 1, 0)
table.cell(dashTable, 0, 1, "━━━━━━━━━━━━━━━━━━━━", text_color=color.rgb(60, 65, 85), text_size=size.tiny, bgcolor=bgColor)
table.merge_cells(dashTable, 0, 1, 1, 1)
sigDisplayColor = currentSignal == "BUY" ? buyColor : currentSignal == "SELL" ? sellColor : waitColor
sigIcon = currentSignal == "BUY" ? "▲" : currentSignal == "SELL" ? "▼" : "◆"
table.cell(dashTable, 0, 2, "SIGNAL", text_color=labelColor, text_size=size.small, bgcolor=bgColor, text_halign=text.align_left)
table.cell(dashTable, 1, 2, sigIcon + " " + currentSignal, text_color=sigDisplayColor, text_size=size.normal, bgcolor=bgColor, text_halign=text.align_right)
entryStr = na(entryPrice) ? "---" : str.tostring(entryPrice, format.mintick)
table.cell(dashTable, 0, 3, " ENTRY", text_color=labelColor, text_size=size.small, bgcolor=bgColor, text_halign=text.align_left)
table.cell(dashTable, 1, 3, entryStr, text_color=textColor, text_size=size.small, bgcolor=bgColor, text_halign=text.align_right)
table.cell(dashTable, 0, 4, "─────────────────────", text_color=color.rgb(50, 55, 75), text_size=size.tiny, bgcolor=bgColor)
table.merge_cells(dashTable, 0, 4, 1, 4)
table.cell(dashTable, 0, 5, " MARKET SESSIONS", text_color=sessionColor, text_size=size.small, bgcolor=headerBg, text_halign=text.align_center)
table.merge_cells(dashTable, 0, 5, 1, 5)
table.cell(dashTable, 0, 6, " ACTIVE NOW", text_color=labelColor, text_size=size.small, bgcolor=bgColor, text_halign=text.align_left)
table.cell(dashTable, 1, 6, currentSession, text_color=activeSessionColor, text_size=size.small, bgcolor=bgColor, text_halign=text.align_right)
sydneyStatus = inSydney ? " " + f_format_time(sydneyRemaining) : " Closed"
table.cell(dashTable, 0, 7, "🇦🇺 Sydney", text_color=labelColor, text_size=size.tiny, bgcolor=bgColor, text_halign=text.align_left)
table.cell(dashTable, 1, 7, sydneyStatus, text_color=inSydney ? activeSessionColor : inactiveSessionColor, text_size=size.tiny, bgcolor=bgColor, text_halign=text.align_right)
tokyoStatus = inTokyo ? " " + f_format_time(tokyoRemaining) : " Closed"
table.cell(dashTable, 0, 8, "🇯🇵 Tokyo", text_color=labelColor, text_size=size.tiny, bgcolor=bgColor, text_halign=text.align_left)
table.cell(dashTable, 1, 8, tokyoStatus, text_color=inTokyo ? activeSessionColor : inactiveSessionColor, text_size=size.tiny, bgcolor=bgColor, text_halign=text.align_right)
londonStatus = inLondon ? " " + f_format_time(londonRemaining) : " Closed"
table.cell(dashTable, 0, 9, "🇬🇧 London", text_color=labelColor, text_size=size.tiny, bgcolor=bgColor, text_halign=text.align_left)
table.cell(dashTable, 1, 9, londonStatus, text_color=inLondon ? activeSessionColor : inactiveSessionColor, text_size=size.tiny, bgcolor=bgColor, text_halign=text.align_right)
newYorkStatus = inNewYork ? " " + f_format_time(newYorkRemaining) : " Closed"
table.cell(dashTable, 0, 10, "🇺🇸 New York", text_color=labelColor, text_size=size.tiny, bgcolor=bgColor, text_halign=text.align_left)
table.cell(dashTable, 1, 10, newYorkStatus, text_color=inNewYork ? activeSessionColor : inactiveSessionColor, text_size=size.tiny, bgcolor=bgColor, text_halign=text.align_right)
table.cell(dashTable, 0, 11, "─────────────────────", text_color=color.rgb(50, 55, 75), text_size=size.tiny, bgcolor=bgColor)
table.merge_cells(dashTable, 0, 11, 1, 11)
barsSince = na(signalBar) ? "---" : str.tostring(bar_index - signalBar)
table.cell(dashTable, 0, 12, "⏱ BARS AGO", text_color=labelColor, text_size=size.tiny, bgcolor=bgColor, text_halign=text.align_left)
table.cell(dashTable, 1, 12, barsSince, text_color=textColor, text_size=size.tiny, bgcolor=bgColor, text_halign=text.align_right)
table.cell(dashTable, 0, 13, " MEOW PURR | @MeowForex1", text_color=authorColor, text_size=size.tiny, bgcolor=headerBg, text_halign=text.align_center)
table.merge_cells(dashTable, 0, 13, 1, 13)
//--------------------------------------------------------------------------------------------------
// Alerts
//--------------------------------------------------------------------------------------------------
alertcondition(finalBuy, title="Buy Signal", message="Breakout System | BUY Signal | Author: MEOW PURR | Telegram: @MeowForex1")
alertcondition(finalSell, title="Sell Signal", message="Breakout System | SELL Signal | Author: MEOW PURR | Telegram: @MeowForex1")