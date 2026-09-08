import React, { useState, useMemo } from "react";
import { TrendingUp, TrendingDown, Minus } from "lucide-react";

const clamp = (n, min, max) => Math.min(max, Math.max(min, n));

export default function StockAnalyzer() {
  const [ticker, setTicker] = useState("INTC");
  const [price, setPrice] = useState(99.16);
  const [ma50, setMa50] = useState(92.46);
  const [ma200, setMa200] = useState(90.03);
  const [rsi, setRsi] = useState(75.5);
  const [expectedMove, setExpectedMove] = useState(19);
  const [ivRank, setIvRank] = useState(28);
  const [sentiment, setSentiment] = useState(1);
  const [catalyst, setCatalyst] = useState("Strong intraday move, +3.51% on the day");
  const [peVsSector, setPeVsSector] = useState(0);
  const [peRatio, setPeRatio] = useState(-45.19);
  const [week52High, setWeek52High] = useState(142.35);
  const [week52Low, setWeek52Low] = useState(24.05);
  const [ivPercentile, setIvPercentile] = useState(30.16);
  const [ema9, setEma9] = useState(96.74);
  const [vwap, setVwap] = useState(98.40);
  const [bbLower, setBbLower] = useState(91.54);
  const [bbMid, setBbMid] = useState(95.26);
  const [bbUpper, setBbUpper] = useState(98.98);
  const [importing, setImporting] = useState(false);
  const [importError, setImportError] = useState("");
  const [importNote, setImportNote] = useState("");
  const [importResults, setImportResults] = useState(null);

  const FIELD_META = [
    { key: "ticker", label: "Ticker" },
    { key: "price", label: "Price" },
    { key: "ma50", label: "SMA 50" },
    { key: "ma200", label: "SMA 200" },
    { key: "ema9", label: "EMA 9" },
    { key: "vwap", label: "VWAP" },
    { key: "rsi", label: "RSI (14)" },
    { key: "bbLower", label: "BB lower" },
    { key: "bbMid", label: "BB mid" },
    { key: "bbUpper", label: "BB upper" },
    { key: "ivRank", label: "IV rank" },
    { key: "ivPercentile", label: "IV percentile" },
    { key: "expectedMove", label: "Expected move %" },
    { key: "peRatio", label: "P/E ratio" },
    { key: "week52High", label: "52-week high" },
    { key: "week52Low", label: "52-week low" },
    { key: "catalyst", label: "Catalyst" },
  ];

  const fileToResizedBase64 = (file, maxDim = 1200) =>
    new Promise((resolve, reject) => {
      const img = new Image();
      const reader = new FileReader();
      reader.onload = () => { img.src = reader.result; };
      reader.onerror = () => reject(new Error("Could not read file"));
      img.onload = () => {
        const scale = Math.min(1, maxDim / Math.max(img.width, img.height));
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(img.width * scale);
        canvas.height = Math.round(img.height * scale);
        const ctx = canvas.getContext("2d");
        ctx.drawImage(img, 0, 0, canvas.width, canvas.height);
        resolve(canvas.toDataURL("image/jpeg", 0.85).split(",")[1]);
      };
      img.onerror = () => reject(new Error("Could not decode image"));
      reader.readAsDataURL(file);
    });

  const extractJson = (text) => {
    const cleaned = text.replace(/```json|```/g, "").trim();
    try {
      return JSON.parse(cleaned);
    } catch {
      const match = cleaned.match(/\{[\s\S]*\}/);
      if (match) return JSON.parse(match[0]);
      throw new Error("No JSON found in model response");
    }
  };

  const handleImageUpload = async (e) => {
    const files = Array.from(e.target.files || []).slice(0, 2);
    if (files.length === 0) return;
    setImporting(true);
    setImportError("");
    setImportNote("");
    setImportResults(null);
    try {
      const imageBlocks = await Promise.all(
        files.map(async (file) => ({
          type: "image",
          source: { type: "base64", media_type: "image/jpeg", data: await fileToResizedBase64(file) },
        }))
      );

      const response = await fetch("https://api.anthropic.com/v1/messages", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          model: "claude-sonnet-4-6",
          max_tokens: 1000,
          messages: [
            {
              role: "user",
              content: [
                ...imageBlocks,
                {
                  type: "text",
                  text:
                    `These are ${imageBlocks.length === 2 ? "two screenshots" : "a screenshot"} of a stock chart, quote screen, or options chain — the data may be split across both images, so combine what you find in each. Look carefully for each of these and read off whatever is visible or reasonably inferable — do not skip a field just because it's small or in a secondary panel: ticker symbol, current price, 50-day moving average (SMA 50), 200-day moving average (SMA 200), 9-period EMA, VWAP, RSI (14-day), Bollinger Bands 20-period (lower/mid/upper), implied volatility rank (0-100), IV percentile (0-100), an expected-move percentage (or derive one from a stated trading range around current price), P/E ratio, and 52-week high/low. Respond ONLY with raw JSON, no markdown fences, no commentary, in exactly this shape: {"ticker": string or null, "price": number or null, "ma50": number or null, "ma200": number or null, "ema9": number or null, "vwap": number or null, "rsi": number or null, "bbLower": number or null, "bbMid": number or null, "bbUpper": number or null, "ivRank": number or null, "ivPercentile": number or null, "expectedMove": number or null, "peRatio": number or null, "week52High": number or null, "week52Low": number or null, "catalyst": string or null, "notes": string describing anything ambiguous}. Use null for any field genuinely not visible in either image — do not guess or omit keys.`,
                },
              ],
            },
          ],
        }),
      });

      if (!response.ok) {
        const errText = await response.text().catch(() => "");
        throw new Error(`API error ${response.status}: ${errText.slice(0, 200)}`);
      }
      const data = await response.json();
      const textBlock = data.content?.find((b) => b.type === "text")?.text || "";
      if (!textBlock) throw new Error("Empty response from model");
      const parsed = extractJson(textBlock);

      if (parsed.ticker) setTicker(String(parsed.ticker).toUpperCase());
      if (typeof parsed.price === "number") setPrice(parsed.price);
      if (typeof parsed.ma50 === "number") setMa50(parsed.ma50);
      if (typeof parsed.ma200 === "number") setMa200(parsed.ma200);
      if (typeof parsed.ema9 === "number") setEma9(parsed.ema9);
      if (typeof parsed.vwap === "number") setVwap(parsed.vwap);
      if (typeof parsed.rsi === "number") setRsi(clamp(parsed.rsi, 0, 100));
      if (typeof parsed.bbLower === "number") setBbLower(parsed.bbLower);
      if (typeof parsed.bbMid === "number") setBbMid(parsed.bbMid);
      if (typeof parsed.bbUpper === "number") setBbUpper(parsed.bbUpper);
      if (typeof parsed.ivRank === "number") setIvRank(clamp(parsed.ivRank, 0, 100));
      if (typeof parsed.ivPercentile === "number") setIvPercentile(clamp(parsed.ivPercentile, 0, 100));
      if (typeof parsed.expectedMove === "number") setExpectedMove(clamp(parsed.expectedMove, 1, 30));
      if (typeof parsed.peRatio === "number") setPeRatio(parsed.peRatio);
      if (typeof parsed.week52High === "number") setWeek52High(parsed.week52High);
      if (typeof parsed.week52Low === "number") setWeek52Low(parsed.week52Low);
      if (parsed.catalyst) setCatalyst(parsed.catalyst);

      setImportResults(
        FIELD_META.map((f) => ({
          ...f,
          found: parsed[f.key] !== null && parsed[f.key] !== undefined && parsed[f.key] !== "",
          value: parsed[f.key],
        }))
      );
      setImportNote(parsed.notes || "");
    } catch (err) {
      setImportError(`Couldn't read those screenshots — ${err.message}. Try clearer crops, or enter values manually.`);
    } finally {
      setImporting(false);
      e.target.value = "";
    }
  };

  const result = useMemo(() => {
    const trendScore = clamp(
      ((price - ma50) / ma50) * 200 + ((ma50 - ma200) / ma200) * 150,
      -25,
      25
    );
    const rsiScore = clamp((rsi - 50) * 0.6, -15, 15);
    const sentimentScore = sentiment * 12;
    const valuationScore = clamp(-peVsSector * 0.8, -10, 10);
    const shortTrendScore = ema9 > 0 ? clamp(((price - ema9) / ema9) * 150, -8, 8) : 0;
    const bandSpan = bbUpper - bbLower;
    const bandScore = bandSpan > 0 ? clamp((((price - bbLower) / bandSpan) - 0.5) * 20, -8, 8) : 0;

    const raw = trendScore + rsiScore + sentimentScore + valuationScore + shortTrendScore + bandScore;
    const composite = clamp(50 + raw, 0, 100);

    let verdict, verdictTone;
    if (composite >= 72) { verdict = "Bullish"; verdictTone = "up"; }
    else if (composite >= 58) { verdict = "Mildly Bullish"; verdictTone = "up"; }
    else if (composite > 42) { verdict = "Neutral"; verdictTone = "flat"; }
    else if (composite > 28) { verdict = "Mildly Bearish"; verdictTone = "down"; }
    else { verdict = "Bearish"; verdictTone = "down"; }

    const moveFrac = expectedMove / 100;
    const bias = (composite - 50) / 50;
    const targetLow = price * (1 + bias * moveFrac * 0.6 - moveFrac * 0.35);
    const targetHigh = price * (1 + bias * moveFrac * 0.6 + moveFrac * 0.65);
    const profitTake = price * (1 + bias * moveFrac * 1.15);
    const stopLevel = price * (1 - moveFrac * 0.5);

    let stockAction;
    if (composite >= 72) stockAction = "Add / Initiate";
    else if (composite >= 58) stockAction = "Hold / Small Add";
    else if (composite > 42) stockAction = "Hold, No Action";
    else if (composite > 28) stockAction = "Trim";
    else stockAction = "Reduce / Exit";

    let optionsView;
    const highIv = ivRank >= 55;
    if (composite >= 58 && highIv) optionsView = "Sell cash-secured puts or put credit spreads — premium is rich, direction favors you.";
    else if (composite >= 58 && !highIv) optionsView = "Buy calls or call debit spreads — cheap premium, favorable trend.";
    else if (composite <= 42 && highIv) optionsView = "Sell call credit spreads — elevated premium, direction favors downside.";
    else if (composite <= 42 && !highIv) optionsView = "Buy puts or put debit spreads — cheap premium, weakening trend.";
    else optionsView = "Premium-neutral setup — consider an iron condor or stand aside until conviction improves.";

    return {
      composite, verdict, verdictTone,
      targetLow, targetHigh, profitTake, stopLevel,
      stockAction, optionsView,
      breakdown: [
        { label: "Trend (price vs MAs)", value: trendScore },
        { label: "Momentum (RSI)", value: rsiScore },
        { label: "News / sentiment", value: sentimentScore },
        { label: "Valuation vs sector", value: valuationScore },
        { label: "Short-term trend (EMA9)", value: shortTrendScore },
        { label: "Band position (BB20)", value: bandScore },
      ],
    };
  }, [price, ma50, ma200, rsi, expectedMove, ivRank, sentiment, peVsSector, ema9, bbLower, bbUpper]);

  const toneColor =
    result.verdictTone === "up" ? "var(--pos)" :
    result.verdictTone === "down" ? "var(--neg)" : "var(--neu)";

  const ToneIcon = result.verdictTone === "up" ? TrendingUp : result.verdictTone === "down" ? TrendingDown : Minus;

  return (
    <div className="wrap">
      <style>{`
        .wrap {
          --ink: #16211D;
          --paper: #F3EFE2;
          --paper2: #E9E3D2;
          --accent: #B8562A;
          --pos: #3F6B4A;
          --neg: #A8412E;
          --neu: #8A7F63;
          --line: rgba(22,33,29,0.14);
          background: var(--ink);
          color: var(--paper);
          font-family: 'Inter', system-ui, sans-serif;
          min-height: 100%;
          padding: 28px 20px 48px;
          font-variant-numeric: tabular-nums;
        }
        .wrap * { box-sizing: border-box; }
        .masthead {
          display: flex;
          justify-content: space-between;
          align-items: baseline;
          border-bottom: 1px solid rgba(243,239,226,0.25);
          padding-bottom: 14px;
          margin-bottom: 22px;
          flex-wrap: wrap;
          gap: 10px;
        }
        .masthead h1 {
          font-family: 'Fraunces', Georgia, serif;
          font-size: 26px;
          font-weight: 600;
          margin: 0;
          letter-spacing: 0.2px;
        }
        .masthead .sub { font-size: 12.5px; color: rgba(243,239,226,0.55); }
        .ticker-input {
          background: transparent;
          border: none;
          border-bottom: 2px solid var(--accent);
          color: var(--paper);
          font-family: 'Fraunces', Georgia, serif;
          font-size: 22px;
          width: 130px;
          padding: 2px 0;
          text-transform: uppercase;
          letter-spacing: 1px;
        }
        .ticker-input:focus { outline: none; }
        .verdict-row {
          display: flex;
          align-items: flex-end;
          gap: 20px;
          flex-wrap: wrap;
          margin-bottom: 26px;
        }
        .verdict-score {
          font-family: 'Fraunces', Georgia, serif;
          font-size: 64px;
          line-height: 1;
          color: var(--tone);
        }
        .verdict-label {
          display: flex;
          align-items: center;
          gap: 8px;
          font-size: 20px;
          font-weight: 600;
          color: var(--tone);
          margin-bottom: 6px;
        }
        .verdict-meta { font-size: 12.5px; color: rgba(243,239,226,0.55); max-width: 320px; }
        .grid {
          display: grid;
          grid-template-columns: 1fr;
          gap: 0;
        }
        @media (min-width: 760px) {
          .grid { grid-template-columns: 1fr 1fr; }
        }
        .panel {
          padding: 18px 20px;
          border-top: 1px solid rgba(243,239,226,0.18);
        }
        .panel h2 {
          font-size: 12px;
          text-transform: none;
          letter-spacing: 0.3px;
          color: var(--accent);
          margin: 0 0 14px;
          font-weight: 600;
        }
        .field { margin-bottom: 12px; }
        .field label {
          display: flex;
          justify-content: space-between;
          font-size: 12.5px;
          color: rgba(243,239,226,0.7);
          margin-bottom: 4px;
        }
        .field input[type="range"] { width: 100%; accent-color: var(--accent); }
        .field input[type="number"], .field input[type="text"] {
          width: 100%;
          background: rgba(243,239,226,0.06);
          border: 1px solid rgba(243,239,226,0.2);
          color: var(--paper);
          padding: 7px 9px;
          border-radius: 3px;
          font-size: 13.5px;
          font-family: inherit;
        }
        .out-panel {
          background: var(--paper);
          color: var(--ink);
          border-radius: 3px;
          padding: 20px;
          margin-top: 6px;
        }
        .out-row {
          display: flex;
          justify-content: space-between;
          padding: 10px 0;
          border-bottom: 1px solid var(--line);
          font-size: 14px;
          gap: 16px;
        }
        .out-row:last-child { border-bottom: none; }
        .out-row .k { color: #5a5647; }
        .out-row .v { font-weight: 600; text-align: right; }
        .action-line {
          font-family: 'Fraunces', Georgia, serif;
          font-size: 18px;
          margin: 0 0 12px;
        }
        .breakdown { margin-top: 18px; }
        .bd-row { display: flex; align-items: center; gap: 10px; margin-bottom: 8px; }
        .bd-label { width: 150px; font-size: 12px; color: rgba(243,239,226,0.65); flex-shrink: 0; }
        .bd-bar-track { flex: 1; height: 6px; background: rgba(243,239,226,0.12); border-radius: 3px; position: relative; }
        .bd-bar-fill { position: absolute; top: 0; bottom: 0; border-radius: 3px; }
        .bd-value { width: 40px; text-align: right; font-size: 12px; color: rgba(243,239,226,0.65); }
        .import-bar {
          display: flex;
          align-items: center;
          gap: 14px;
          flex-wrap: wrap;
          margin-bottom: 4px;
        }
        .import-btn {
          position: relative;
          background: var(--accent);
          color: var(--paper);
          font-size: 13px;
          font-weight: 600;
          padding: 9px 16px;
          border-radius: 3px;
          cursor: pointer;
          display: inline-block;
        }
        .import-btn input { position: absolute; inset: 0; opacity: 0; cursor: pointer; }
        .import-note { font-size: 12px; color: rgba(243,239,226,0.6); max-width: 420px; }
        .import-error { font-size: 12px; color: #E28A7A; max-width: 420px; }
        .checklist {
          display: flex;
          flex-wrap: wrap;
          gap: 6px 10px;
          background: rgba(243,239,226,0.05);
          border: 1px solid rgba(243,239,226,0.15);
          border-radius: 4px;
          padding: 12px 14px;
          margin-bottom: 18px;
        }
        .chk-item {
          display: flex;
          align-items: baseline;
          gap: 5px;
          font-size: 12px;
          padding: 2px 8px 2px 0;
        }
        .chk-mark { width: 13px; font-weight: 700; }
        .chk-yes .chk-mark { color: var(--pos); }
        .chk-no .chk-mark { color: rgba(243,239,226,0.35); }
        .chk-yes .chk-label { color: rgba(243,239,226,0.9); }
        .chk-no .chk-label { color: rgba(243,239,226,0.4); }
        .chk-val { color: rgba(243,239,226,0.5); }
        .chk-note {
          flex-basis: 100%;
          font-size: 11.5px;
          color: rgba(243,239,226,0.5);
          margin-top: 6px;
          border-top: 1px solid rgba(243,239,226,0.1);
          padding-top: 8px;
        }
        .disclaimer {
          margin-top: 26px;
          font-size: 11.5px;
          color: rgba(243,239,226,0.45);
          border-top: 1px solid rgba(243,239,226,0.15);
          padding-top: 14px;
          max-width: 640px;
        }
      `}</style>

      <div className="masthead">
        <div>
          <h1>Analyst Worksheet</h1>
          <div className="sub">Composite read from your own inputs — not a live data feed</div>
        </div>
        <input
          className="ticker-input"
          value={ticker}
          onChange={(e) => setTicker(e.target.value.toUpperCase())}
          maxLength={6}
        />
      </div>

      <div className="verdict-row">
        <div className="verdict-score" style={{ "--tone": toneColor }}>
          {Math.round(result.composite)}
        </div>
        <div>
          <div className="verdict-label" style={{ "--tone": toneColor }}>
            <ToneIcon size={20} />
            {result.verdict}
          </div>
          <div className="verdict-meta">
            Composite of trend, momentum, sentiment and valuation, scaled 0 (max bearish) to 100 (max bullish).
          </div>
        </div>
      </div>

      <div className="import-bar">
        <label className="import-btn">
          {importing ? "Reading charts…" : "Upload chart screenshots (up to 2)"}
          <input type="file" accept="image/*" multiple onChange={handleImageUpload} disabled={importing} />
        </label>
        {importError && <span className="import-error">{importError}</span>}
      </div>

      {importResults && (
        <div className="checklist">
          {importResults.map((f) => (
            <div className={`chk-item ${f.found ? "chk-yes" : "chk-no"}`} key={f.key}>
              <span className="chk-mark">{f.found ? "✓" : "–"}</span>
              <span className="chk-label">{f.label}</span>
              {f.found && <span className="chk-val">{typeof f.value === "number" ? f.value : String(f.value).slice(0, 22)}</span>}
            </div>
          ))}
          {importNote && <div className="chk-note">{importNote}</div>}
        </div>
      )}

      <div className="grid">
        <div className="panel">
          <h2>Technicals</h2>
          <div className="field">
            <label><span>Current price</span><span>${price}</span></label>
            <input type="number" value={price} step="0.5" onChange={(e) => setPrice(parseFloat(e.target.value) || 0)} />
          </div>
          <div className="field">
            <label><span>50-day moving average</span><span>${ma50}</span></label>
            <input type="number" value={ma50} step="0.5" onChange={(e) => setMa50(parseFloat(e.target.value) || 0)} />
          </div>
          <div className="field">
            <label><span>200-day moving average</span><span>${ma200}</span></label>
            <input type="number" value={ma200} step="0.5" onChange={(e) => setMa200(parseFloat(e.target.value) || 0)} />
          </div>
          <div className="field">
            <label><span>9-period EMA</span><span>${ema9}</span></label>
            <input type="number" value={ema9} step="0.5" onChange={(e) => setEma9(parseFloat(e.target.value) || 0)} />
          </div>
          <div className="field">
            <label><span>VWAP</span><span>${vwap}</span></label>
            <input type="number" value={vwap} step="0.5" onChange={(e) => setVwap(parseFloat(e.target.value) || 0)} />
          </div>
          <div className="field">
            <label><span>RSI (14-day)</span><span>{rsi}</span></label>
            <input type="range" min="0" max="100" value={rsi} onChange={(e) => setRsi(parseInt(e.target.value))} />
          </div>
          <div className="field">
            <label><span>Bollinger Bands (20) — lower / mid / upper</span></label>
            <div style={{ display: "flex", gap: "8px" }}>
              <input type="number" value={bbLower} step="0.5" onChange={(e) => setBbLower(parseFloat(e.target.value) || 0)} />
              <input type="number" value={bbMid} step="0.5" onChange={(e) => setBbMid(parseFloat(e.target.value) || 0)} />
              <input type="number" value={bbUpper} step="0.5" onChange={(e) => setBbUpper(parseFloat(e.target.value) || 0)} />
            </div>
          </div>
        </div>

        <div className="panel">
          <h2>Sentiment, options & valuation</h2>
          <div className="field">
            <label><span>News / narrative tone</span><span>{["Very bearish","Bearish","Neutral","Bullish","Very bullish"][sentiment + 2]}</span></label>
            <input type="range" min="-2" max="2" value={sentiment} onChange={(e) => setSentiment(parseInt(e.target.value))} />
          </div>
          <div className="field">
            <label><span>Key catalyst / headline</span></label>
            <input type="text" value={catalyst} onChange={(e) => setCatalyst(e.target.value)} />
          </div>
          <div className="field">
            <label><span>Expected move (earnings/IV, %)</span><span>{expectedMove}%</span></label>
            <input type="range" min="1" max="30" value={expectedMove} onChange={(e) => setExpectedMove(parseInt(e.target.value))} />
          </div>
          <div className="field">
            <label><span>IV rank</span><span>{ivRank}</span></label>
            <input type="range" min="0" max="100" value={ivRank} onChange={(e) => setIvRank(parseInt(e.target.value))} />
          </div>
          <div className="field">
            <label><span>IV percentile</span><span>{ivPercentile}</span></label>
            <input type="range" min="0" max="100" value={ivPercentile} onChange={(e) => setIvPercentile(parseInt(e.target.value))} />
          </div>
          <div className="field">
            <label><span>P/E ratio</span><span>{peRatio}</span></label>
            <input type="number" value={peRatio} step="0.1" onChange={(e) => setPeRatio(parseFloat(e.target.value) || 0)} />
          </div>
          <div className="field">
            <label><span>P/E vs sector avg (%)</span><span>{peVsSector > 0 ? "+" : ""}{peVsSector}%</span></label>
            <input type="range" min="-40" max="40" value={peVsSector} onChange={(e) => setPeVsSector(parseInt(e.target.value))} />
          </div>
          <div className="field">
            <label><span>52-week range</span></label>
            <div style={{ display: "flex", gap: "8px" }}>
              <input type="number" value={week52Low} step="0.5" onChange={(e) => setWeek52Low(parseFloat(e.target.value) || 0)} />
              <input type="number" value={week52High} step="0.5" onChange={(e) => setWeek52High(parseFloat(e.target.value) || 0)} />
            </div>
          </div>
        </div>
      </div>

      <div className="out-panel">
        <p className="action-line">{ticker} — {result.stockAction}</p>
        <div className="out-row"><span className="k">Price target range</span><span className="v">${result.targetLow.toFixed(2)} – ${result.targetHigh.toFixed(2)}</span></div>
        <div className="out-row"><span className="k">Profit-taking level</span><span className="v">${result.profitTake.toFixed(2)}</span></div>
        <div className="out-row"><span className="k">Suggested stop / trim trigger</span><span className="v">${result.stopLevel.toFixed(2)}</span></div>
        <div className="out-row"><span className="k">Options stance</span><span className="v">{result.optionsView}</span></div>
        <div className="out-row"><span className="k">P/E · IV percentile</span><span className="v">{peRatio} · {ivPercentile}</span></div>
        <div className="out-row"><span className="k">52-week range</span><span className="v">${week52Low.toFixed(2)} – ${week52High.toFixed(2)}</span></div>
        <div className="out-row"><span className="k">Catalyst on file</span><span className="v">{catalyst || "—"}</span></div>
      </div>

      <div className="breakdown">
        {result.breakdown.map((b) => {
          const pct = clamp((b.value + 25) / 50, 0, 1) * 100;
          const color = b.value >= 0 ? "var(--pos)" : "var(--neg)";
          return (
            <div className="bd-row" key={b.label}>
              <div className="bd-label">{b.label}</div>
              <div className="bd-bar-track">
                <div className="bd-bar-fill" style={{ left: "50%", width: `${Math.abs(pct - 50)}%`, background: color, ...(pct < 50 ? { left: `${pct}%` } : {}) }} />
              </div>
              <div className="bd-value">{b.value > 0 ? "+" : ""}{b.value.toFixed(0)}</div>
            </div>
          );
        })}
      </div>

      <div className="disclaimer">
        This worksheet runs entirely on the numbers you enter — it has no live market data connection. Treat every output as a way to pressure-test your own thesis, not as investment advice. Price targets and options stances are derived from simple weighted rules you can (and should) adjust once this moves to a real data pipeline.
      </div>
    </div>
  );
}
