"""
Scanner 03 — NSE Breakout Watch
Full port of nse-swing.py from nse-swing-screener repo.
Original warm-paper aesthetic restyled to gold/dark RH terminal.

8 CMT-grade filters:
  1. Nifty regime (>50MA)
  2. Relative Strength vs Nifty (3M)
  3. ATR-normalized distance
  4. Tight base (15d SD ≤ 4%)
  5. Wyckoff up/down volume ratio
  6. Resistance level integrity
  7. Chop-zone rejection
  8. 2-candle or 1.5× volume confirmation
"""
import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import os, sys

sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from theme import (
    apply_theme, render_header,
    RH_MAROON, RH_MAROON_DK, RH_GOLD, RH_GOLD_LIGHT, RH_GOLD_DIM,
    RH_RED, RH_GREEN, RH_BG, RH_SURFACE, RH_SURFACE2, RH_TEXT, RH_MUTED, RH_BORDER
)
from auth import require_login, render_logout_button

st.set_page_config(layout="wide", page_title="RH | Breakout Watch",
                   initial_sidebar_state="expanded")
apply_theme()
require_login()
render_logout_button()
render_header("Scanner 03 · NSE Breakout Watch")


# ─────────────────────────────────────────────────────
#  PAGE-SPECIFIC STYLES (custom tables, pills, KPI tiles)
# ─────────────────────────────────────────────────────
st.markdown(f"""
<style>
/* KPI row */
.kpi-row {{
    display: grid;
    grid-template-columns: repeat(5, 1fr);
    gap: 10px;
    margin-bottom: 22px;
}}
.kpi {{
    background: {RH_SURFACE};
    border: 1px solid {RH_BORDER};
    padding: 14px 16px;
    text-align: center;
    transition: border-color 0.2s ease;
}}
.kpi:hover {{ border-color: {RH_GOLD_DIM}; }}
.kpi-val {{
    font-family: 'Fraunces', serif;
    font-size: 1.9rem;
    font-weight: 900;
    line-height: 1;
    letter-spacing: -0.02em;
}}
.kpi-lbl {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.62rem;
    color: {RH_MUTED};
    text-transform: uppercase;
    letter-spacing: 0.16em;
    margin-top: 8px;
    font-weight: 400;
}}

/* Custom data table */
.tbl {{
    background: {RH_SURFACE};
    border: 1px solid {RH_BORDER};
    overflow: hidden;
    margin-bottom: 8px;
}}
.tbl-hdr {{
    display: grid;
    grid-template-columns: 110px 100px 115px 130px 150px 100px 105px 95px;
    padding: 10px 22px;
    background: {RH_SURFACE2};
    border-bottom: 1px solid {RH_BORDER};
}}
.tbl-hdr span {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.6rem;
    color: {RH_GOLD_DIM};
    text-transform: uppercase;
    letter-spacing: 0.16em;
    font-weight: 500;
}}
.tbl-row {{
    display: grid;
    grid-template-columns: 110px 100px 115px 130px 150px 100px 105px 95px;
    padding: 14px 22px;
    border-bottom: 1px solid rgba(58,53,48,0.5);
    transition: background 0.12s;
    align-items: center;
}}
.tbl-row:hover {{ background: rgba(184,136,26,0.04); }}
.tbl-row:last-child {{ border-bottom: none; }}
.scroll-body {{ max-height: 520px; overflow-y: auto; }}
.scroll-body::-webkit-scrollbar {{ width: 4px; }}
.scroll-body::-webkit-scrollbar-track {{ background: {RH_SURFACE}; }}
.scroll-body::-webkit-scrollbar-thumb {{ background: {RH_GOLD_DIM}; }}

.sym {{
    font-family: 'Fraunces', serif;
    font-weight: 700;
    font-size: 1.0rem;
    color: {RH_TEXT};
    letter-spacing: -0.01em;
}}
.mono {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.78rem;
    color: {RH_TEXT};
}}

/* Tier pills */
.pill {{
    display: inline-block;
    padding: 3px 10px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.6rem;
    font-weight: 500;
    letter-spacing: 0.12em;
}}
.pill-hot  {{ background: rgba(231,76,60,0.08);  color: {RH_RED};         border: 1px solid rgba(231,76,60,0.4); }}
.pill-warm {{ background: rgba(212,168,48,0.08); color: {RH_GOLD_LIGHT};  border: 1px solid rgba(212,168,48,0.4); }}
.pill-cool {{ background: rgba(142,111,216,0.08); color: #8E6FD8;          border: 1px solid rgba(142,111,216,0.4); }}

/* Sector tag */
.sec {{
    display: inline-block;
    padding: 2px 7px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.58rem;
    font-weight: 500;
    letter-spacing: 0.1em;
    text-transform: uppercase;
}}

/* Proximity bar */
.prox {{ display: flex; align-items: center; gap: 8px; }}
.prox-bg {{
    flex: 1;
    height: 4px;
    background: rgba(58,53,48,0.5);
    overflow: hidden;
}}
.prox-fill {{ height: 100%; }}

/* Section headings */
.section-head {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.72rem;
    color: {RH_GOLD_DIM};
    margin: 26px 0 12px;
    display: flex;
    align-items: baseline;
    gap: 14px;
    letter-spacing: 0.16em;
    text-transform: uppercase;
    font-weight: 400;
}}
.section-head::after {{
    content: '';
    flex: 1;
    height: 1px;
    background: {RH_BORDER};
    position: relative;
    top: -3px;
}}
.section-head-label {{
    color: {RH_GOLD_LIGHT};
    font-weight: 500;
}}

/* Empty state */
.empty-state {{
    text-align: center;
    padding: 80px 20px;
}}
.empty-state-orn {{
    font-family: 'Fraunces', serif;
    font-size: 3rem;
    color: {RH_GOLD_DIM};
    margin-bottom: 14px;
    line-height: 1;
}}
.empty-state-text {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.95rem;
    color: {RH_TEXT};
    letter-spacing: 0.08em;
    text-transform: uppercase;
}}
.empty-state-sub {{
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.7rem;
    color: {RH_MUTED};
    margin-top: 8px;
    letter-spacing: 0.06em;
}}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{
    gap: 24px;
    border-bottom: 1px solid {RH_BORDER};
    background: transparent !important;
    padding: 0 4px;
}}
.stTabs [data-baseweb="tab"] {{
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.72rem !important;
    color: {RH_MUTED} !important;
    background: transparent !important;
    padding: 10px 0 !important;
    border: none !important;
    letter-spacing: 0.12em !important;
    text-transform: uppercase;
}}
.stTabs [aria-selected="true"] {{
    color: {RH_GOLD_LIGHT} !important;
    border-bottom: 2px solid {RH_GOLD} !important;
}}

/* Sidebar slider labels */
[data-testid="stSidebar"] .stSlider label,
[data-testid="stSidebar"] .stCheckbox label {{
    color: {RH_GOLD_DIM} !important;
    font-family: 'IBM Plex Mono', monospace !important;
    font-size: 0.62rem !important;
    text-transform: uppercase;
    letter-spacing: 0.12em !important;
    font-weight: 500 !important;
}}
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  WATCHLIST + SECTOR MAP
# ═══════════════════════════════════════════════════════════════
WATCHLIST = [
  "STLTECH.NS","NEUEON.NS","MTARTECH.NS","PRIZOR.NS","OMNI.NS","ATLANTAELE.NS","QPOWER.NS","DEEDEV.NS","KSHINTL.NS","KRN.NS",
    "GVPIL.NS","BAJAJCON.NS","POWERINDIA.NS","KAPSTON.NS","VIDYAWIRES.NS","PRECWIRE.NS","BHAGYANGR.NS","AVANTIFEED.NS","UNIHEALTH.NS","SUNLITE.NS",
    "APEX.NS","DPEL.NS","BLISSGVS.NS","SPORTKING.NS","ANTELOPUS.NS","NGLFINE.NS","ROSSTECH.NS","GALLANTT.NS","SCHNEIDER.NS","INA.NS",
    "LOKESHMACH.NS","TDPOWERSYS.NS","CONFIPET.NS","PARKHOSPS.NS","UFBL.NS","HFCL.NS","CPPLUS.NS","DBOL.NS","INDOTECH.NS","SANSERA.NS",
    "ADANIPOWER.NS","HARDWYN.NS","SAKAR.NS","DATAPATTNS.NS","INDSWFTLAB.NS","AEROFLEX.NS","E2E.NS","WELCORP.NS","JNKINDIA.NS","VOLTAMP.NS",
    "APOLLOPIPE.NS","GAUDIUMIVF.NS","STEELCAS.NS","KRITINUT.NS","NITINSPIN.NS","SGMART.NS","AMCL.NS","SBCL.NS","AEQUS.NS","GVT&D.NS",
    "ACUTAAS.NS","VMARCIND.NS","GNA.NS","TMB.NS","KIRLPNU.NS","JINDALSAW.NS","RUBICON.NS","S&SPOWER.NS","STYLEBAAZA.NS","GUJALKALI.NS",
    "RAMRAT.NS","SEAMECLTD.NS","ADVAIT.NS","KIRLOSENG.NS","AXISCADES.NS","APARINDS.NS","ABB.NS","EMMVEE.NS","SILVERTUC.NS","GROWW.NS",
    "DANISH.NS","ADANIENSOL.NS","NEOGEN.NS","NATIONALUM.NS","JINDALPOLY.NS","JYOTISTRUC.NS","VTL.NS","SHADOWFAX.NS","SIGMAADV.NS","MANINDS.NS",
    "UTLSOLAR.NS","LUXIND.NS","HMT.NS","SALSTEEL.NS","AETHER.NS","BSE.NS","AGIIL.NS","PRECOT.NS","WEBELSOLAR.NS","RPTECH.NS",
    "ALPEXSOLAR.NS","TORNTPOWER.NS","EBGNG.NS","ANGELONE.NS","MMFL.NS","SHILCTECH.NS","JTLIND.NS","AARTIIND.NS","PCCL.NS","CONSOFINVT.NS",
    "PFC.NS","THERMAX.NS","SHARDACROP.NS","FINCABLES.NS","TIRUPATIFL.NS","BUILDPRO.NS","AZAD.NS","LLOYDSME.NS","SYRMA.NS","LINCOLN.NS",
    "PFOCUS.NS","KRISHNADEF.NS","SUVEN.NS","KSB.NS","PAISALO.NS","STLNETWORK.NS","INOXINDIA.NS","SGFIN.NS","POWERICA.NS","RMC.NS",
    "ABSLAMC.NS","NINSYS.NS","SKYGOLD.NS","PREMIERPOL.NS","SUPREMEPWR.NS","ANDHRSUGAR.NS","ARFIN.NS","ADFFOODS.NS","MCX.NS","MAHLOG.NS",
    "GESHIP.NS","NELCAST.NS","J&KBANK.NS","NETWEB.NS","SHILPAMED.NS","BHARATFORG.NS","SCI.NS","ACMESOLAR.NS","SAATVIKGL.NS","CGPOWER.NS",
    "AMAGI.NS","AMBER.NS","BODALCHEM.NS","KAJARIACER.NS","UEL.NS","AVADHSUGAR.NS","KTKBANK.NS","ENGINERSIN.NS","KRISHANA.NS","AYMSYNTEX.NS",
    "GANESHBE.NS","MAHABANK.NS","SUYOG.NS","GRWRHITECH.NS","SMSPHARMA.NS","NLCINDIA.NS","PTC.NS","ENRIN.NS","CHENNPETRO.NS","GSPCROP.NS",
    "SAIL.NS","SWANDEF.NS","DYNAMATECH.NS","GOKULAGRO.NS","ARVIND.NS","BANDHANBNK.NS","CELLECOR.NS","SIEMENS.NS","OFSS.NS","ICICIAMC.NS",
    "CENTUM.NS","GULPOLY.NS","SAMBHV.NS","SOLARINDS.NS","ONGC.NS","MBAPL.NS","VENUSPIPES.NS","THANGAMAYL.NS","SEDEMAC.NS","DALMIASUG.NS",
    "NTPC.NS","ATHERENERG.NS","VEDL.NS","SHRIAHIMSA.NS","OBSCP.NS","SONACOMS.NS","NAHARSPING.NS","WHEELS.NS","RHETAN.NS","BHARATWIRE.NS",
    "ZENTEC.NS","AMBIKCO.NS","PRAJIND.NS","NTPCGREEN.NS","AIMTRON.NS","INGERRAND.NS","PIRAMALFIN.NS","PREMIERENE.NS","LINDEINDIA.NS","AMANTA.NS",
    "VIVIDEL.NS","JAYNECOIND.NS","HONASA.NS","SOUTHWEST.NS","ACCENTMIC.NS","KECL.NS","ADANIGREEN.NS","UNIMECH.NS","BHEL.NS","MEGATHERM.NS",
    "SAIPARENT.NS","CEIGALL.NS","SUTLEJTEX.NS","BEEKAY.NS","CORONA.NS","IDEAFORGE.NS","BHAGCHEM.NS","POWERGRID.NS","SINDHUTRAD.NS","TATAPOWER.NS",
    "GANECOS.NS","NATCOPHARM.NS","HIRECT.NS","HINDALCO.NS","DMART.NS","EMCURE.NS","LIKHITHA.NS","REGAAL.NS","ISGEC.NS","JSWENERGY.NS",
    "PITTIENG.NS","UNITEDPOLY.NS","JINDALSTEL.NS","SPLPETRO.NS","SERVOTECH.NS","MANGLMCEM.NS","AUROPHARMA.NS","DIVGIITTS.NS","ANTHEM.NS","SPMLINFRA.NS",
    "SIGNPOST.NS","MIRCELECTR.NS","KANPRPLA.NS","IRMENERGY.NS","GMDCLTD.NS","SATIN.NS","TATASTEEL.NS","GHCLTEXTIL.NS","AVALON.NS","BBL.NS",
    "WSTCSTPAPR.NS","NOCIL.NS","LENSKART.NS","SBC.NS","MWL.NS","EMIL.NS","HSCL.NS","VENUSREM.NS","STYRENIX.NS","LLOYDSENT.NS",
    "GLENMARK.NS","CUMMINSIND.NS","NAVA.NS","KARNIKA.NS","TIPSMUSIC.NS","AKUMS.NS","TIMKEN.NS","TARIL.NS","ENTERO.NS","PARAS.NS",
    "WELSPLSOL.NS","BALAMINES.NS","GRANULES.NS","TRUALT.NS","RISHABH.NS","CCL.NS","GRSE.NS","KRYSTAL.NS","WALCHANNAG.NS","DIACABS.NS",
    "COALINDIA.NS","TECHNOE.NS","OIL.NS","FRESHARA.NS","PRIVISCL.NS","ELGIEQUIP.NS","NAM_INDIA.NS","GOCLCORP.NS","SAILIFE.NS","AYE.NS",
    "STAR.NS","MENONBE.NS","ASHIANA.NS","BELRISE.NS","WABAG.NS","BMWVENTLTD.NS","FINEORG.NS","WAAREEENER.NS","SARDAEN.NS","WANBURY.NS",
    "MCLEODRUSS.NS","BORANA.NS","MAHSEAMLES.NS","JGCHEM.NS","JSFB.NS","GPIL.NS","EDELWEISS.NS","ANANDRATHI.NS","HCC.NS","DELHIVERY.NS",
    "TIINDIA.NS","ATGL.NS","ROLEXRINGS.NS","ASTERDM.NS","JPPOWER.NS","NEPHROPLUS.NS","FUSION.NS","PICCADIL.NS","MARSONS.NS","MRPL.NS",
    "SPAL.NS","GRAPHITE.NS","TALBROAUTO.NS","KSOLVES.NS","DYCL.NS","KIRANVYPAR.NS","BALRAMCHIN.NS","GOODLUCK.NS","HAPPYFORGE.NS","NITTAGELA.NS",
    "PRAVEG.NS","RACLGEAR.NS","SUDEEPPHRM.NS","PNGSREVA.NS","VIVIANA.NS","HALDYNGL.NS","SOMANYCERA.NS","RSL.NS","SESHAPAPER.NS","STARHEALTH.NS",
    "VILAS.NS","RATNAMANI.NS","YATHARTH.NS","ATUL.NS","DHANBANK.NS","CARBORUNIV.NS","ZODIAC.NS","SADHNANIQ.NS","IFCI.NS","MODIS.NS",
    "MIDHANI.NS","ADVENZYMES.NS","CESC.NS","SUNCLAY.NS","MAYURUNIQ.NS","BBOX.NS","POLYPLEX.NS","TFCILTD.NS","DWARKESH.NS","KARURVYSYA.NS",
    "CIEINDIA.NS","ASTRAMICRO.NS","APOLLO.NS","ABSMARINE.NS","JBCHEPHARM.NS","DHAMPURSUG.NS","GLOBAL.NS","TIIL.NS","RAJOOENG.NS","SEIL.NS",
    "PRUDENT.NS","TIMEX.NS","RKFORGE.NS","INFLUX.NS","ELPROINTL.NS","APTECHT.NS","GREENPOWER.NS","GODAVARIB.NS","FAZE3Q.NS","DCBBANK.NS",
    "ASIANENE.NS","GKSL.NS","NESTLEIND.NS","SBIN.NS","JAIBALAJI.NS","TENNIND.NS","URJA.NS","NAVINFLUOR.NS","SWARAJENG.NS","SENORES.NS",
    "PROZONER.NS","ADANIPORTS.NS","VOLTAS.NS","GANDHITUBE.NS","ALIVUS.NS","SCHAEFFLER.NS","UNIONBANK.NS","VIESL.NS","MACPOWER.NS","RAYMOND.NS",
    "UTSSAV.NS","KOTIC.NS","TRAVELFOOD.NS","PNGJL.NS","WHIRLPOOL.NS","KERNEX.NS","ASTRAL.NS","DMCC.NS","ASAL.NS","JSWSTEEL.NS",
    "KEI.NS","IOLCP.NS","TAKE.NS","APOLLOHOSP.NS","KABRAEXTRU.NS","RSWM.NS","RPSGVENT.NS","POKARNA.NS","SOLEX.NS","SPARC.NS",
    "LTFOODS.NS","BENGALASM.NS","TITAN.NS","TORNTPHARM.NS","ACI.NS","NMDC.NS","CMPDI.NS","COMSYN.NS","SHREEJISPG.NS","MANORAMA.NS",
    "SHANTIGOLD.NS","BEPL.NS","KIMS.NS","MEDPLUS.NS","RRKABEL.NS","WAAREERTL.NS","LUPIN.NS","ATULAUTO.NS","FEDERALBNK.NS","BLUESTARCO.NS",
    "BEL.NS","GAEL.NS","POWERMECH.NS","SUNFLAG.NS","PNBHOUSING.NS","VISHNU.NS","IMFA.NS","SUZLON.NS","FRACTAL.NS","BLUESTONE.NS",
    "SKIPPER.NS","NAHARPOLY.NS","HINDCOMPOS.NS","SUPREMEIND.NS","JITFINFRA.NS","VESUVIUS.NS","INDPRUD.NS","ARROWGREEN.NS","IPCALAB.NS","SWELECTES.NS",
    "JAINREC.NS","DICIND.NS","TEJASCARGO.NS","TRANSRAILL.NS","GRPLTD.NS","AEROENTER.NS","SJVN.NS","PARIN.NS","POLYCAB.NS","SHRIPISTON.NS",
    "DLINKINDIA.NS","WELINV.NS","HESTERBIO.NS","APCOTEXIND.NS","LUMAXTECH.NS","UNIPARTS.NS","JPOLYINVST.NS","KENNAMET.NS","OAL.NS","FORTIS.NS",
    "XPROINDIA.NS","ORICONENT.NS","MAZDOCK.NS","MARINE.NS","AVL.NS","SSWL.NS","TRITURBINE.NS","INDIANB.NS","ELECTCAST.NS","OMPOWER.NS",
    "ZYDUSWELL.NS","HINDCOPPER.NS","PYRAMID.NS","SANATHAN.NS","PIXTRANS.NS","CUPID.NS","JAGSNPHARM.NS","CEINSYS.NS","DRREDDY.NS","CLSEL.NS",
    "NHPC.NS","URBANCO.NS","EASEMYTRIP.NS","PASHUPATI.NS","GGBL.NS","SIS.NS","WINDLAS.NS","TANLA.NS","CROMPTON.NS","DHARMAJ.NS",
    "TVSELECT.NS","UJJIVANSFB.NS","VBL.NS","TNPL.NS","DECNGOLD.NS","IGPL.NS","FOCUS.NS","OLECTRA.NS","ASHIKA.NS","REDTAPE.NS",
    "ORIENTELEC.NS","EQUITASBNK.NS","CARRARO.NS","HEXATRADEX.NS","AWHCL.NS","RENUKA.NS","ADANIENT.NS","EFFWA.NS","GOLDIAM.NS","KIRLOSBROS.NS",
    "DRAGARWQ.NS","TVSSCS.NS","GUJAPOLLO.NS","RUBYMILLS.NS","DEEPINDS.NS","SATIA.NS","DELTACORP.NS","SIKA.NS","ZSARACOM.NS","ARVSMART.NS",
    "IONEXCHANG.NS","GICRE.NS","MUTHOOTMF.NS","KIOCL.NS","GTLINFRA.NS","YASHO.NS","NRBBEARING.NS","SURYODAY.NS","NOVARTIND.NS","IGIL.NS",
    "LGEINDIA.NS","HEG.NS","GVKPIL.NS","PATELRMART.NS","INDOTHAI.NS","TATACHEM.NS","SANGAMIND.NS","RECLTD.NS","APS.NS","BCLIND.NS",
    "SURAKSHA.NS","NORTHARC.NS","EPL.NS","BAJEL.NS","VIJAYA.NS","MOTHERSON.NS","STEELXIND.NS","KINGFA.NS","COSMOFIRST.NS","RTNPOWER.NS",
    "TATAINVEST.NS","EIEL.NS","EKC.NS","NIACL.NS","PVRINOX.NS","GRAUWEIL.NS","BIL.NS","BAJAJHIND.NS","LLOYDSENGG.NS","KSL.NS",
    "SHYAMMETL.NS","TVSHLTD.NS","MCLOUD.NS","COCHINSHIP.NS","SANOFICONR.NS","NIRLON.NS","JSWCEMENT.NS","WINDMACHIN.NS","DSSL.NS","TILPP.E1.NS",
    "KOPRAN.NS","KOTHARIPET.NS","MARICO.NS","TEMBO.NS","SHAILY.NS","BIRLAMONEY.NS","DCXINDIA.NS","WPIL.NS","ANONDITA.NS","HDFCAMC.NS",
    "STARCEMENT.NS","BOSCHLTD.NS","HINDOILEXP.NS","PREMEXPLN.NS","MUNJALSHOW.NS","GODREJAGRO.NS","RADICO.NS","RATNAVEER.NS","EXCELSOFT.NS","SNOWMAN.NS",
    "GRINDWELL.NS","TRIVENI.NS","PAGEIND.NS","KIRLOSIND.NS","AUBANK.NS","MOREPENLAB.NS","IRB.NS","TRANSPEK.NS","SOUTHBANK.NS","KOVAI.NS",
    "VSSL.NS","HARSHA.NS","ZEEL.NS","SAHANA.NS","KPIL.NS","AVTNPL.NS","MANKIND.NS","EPACK.NS","JBMA.NS","JKPAPER.NS",
    "PRINCEPIPE.NS","GLOTTIS.NS","CHEVIOT.NS","SGIL.NS","VENKEYS.NS","RBLBANK.NS","GLAND.NS","INDUSINDBK.NS","MUKANDLTD.NS","REFEX.NS",
    "EIMCOELECO.NS","JUBLINGREA.NS","KAYNES.NS","MUNJALAU.NS","NIVABUPA.NS","NAVNETEDUL.NS","OBEROIRLTY.NS","TVSMNCRPS.P1.NS","ORKLAINDIA.NS","INDIASHLTR.NS",
    "NXST.RR.NS","GPTINFRA.NS","HOMEFIRST.NS","CARYSIL.NS","CGCL.NS","APLAPOLLO.NS","BAJAJ_AUTO.NS","KDDL.NS","NRAIL.NS","LICHSGFIN.NS",
    "AXISBANK.NS","PTL.NS","BAHETI.NS","CAMS.NS","BRIGHOTEL.NS","WEALTH.NS","CLEANMAX.NS","MARKSANS.NS","VALIANTORG.NS","PRIMESECU.NS",
    "AADHARHFC.NS","SUNPHARMA.NS","KPEL.NS","VGUARD.NS","SAREGAMA.NS","NYKAA.NS","EXCELINDUS.NS","NAVKARCORP.NS","ASTEC.NS","BNAGROCHEM.NS",
    "5PAISA.NS","BAYERCROP.NS","DPSCLTD.NS","COLPAL.NS","GENUSPOWER.NS","HINDZINC.NS","BFINVEST.NS","MINDTECK.NS","GCSL.NS","MAGADSUGAR.NS",
    "RBA.NS","THEJO.NS","JAYBARMARU.NS","MOSCHIP.NS","FERMENTA.NS","RBZJEWEL.NS","ELANTAS.NS","GEMAROMA.NS","GRMOVER.NS","KOKUYOCMLN.NS",
    "ZFSTEERING.NS","MMP.NS","NCC.NS","KROSS.NS","ASTAR.NS","VIYASH.NS","DIVISLAB.NS","SHANTIGEAR.NS","SAHASRA.NS","STYLAMIND.NS",
    "AFSL.NS","VHLTD.NS","ESABINDIA.NS","WELSPUNLIV.NS","EXICOM.NS","WELENT.NS","GLOBUSSPR.NS","INNOVACAP.NS","MGL.NS","ULTRACEMCO.NS",
    "GABRIEL.NS","MUFIN.NS","ANUHPHR.NS","VINYAS.NS","FLAIR.NS","PRAKASH.NS","SENCO.NS","JSWINFRA.NS","FEDFINA.NS","NATIONSTD.NS",
    "USHAMART.NS","63MOONS.NS","SUNTV.NS","MUKKA.NS","MCCHRLS_B.NS","CAPACITE.NS","FINPIPE.NS","ANURAS.NS","ZFCVINDIA.NS","VSTIND.NS",
    "SCHAND.NS","IMAGICAA.NS","ELECON.NS","AUTOAXLES.NS","NILKAMAL.NS","ITDC.NS","BANKINDIA.NS","CCCL.NS","HATSUN.NS","SUKHJITS.NS",
    "CARERATING.NS","WONDERLA.NS","PCJEWELLER.NS","COCKERILL.NS","TMCV.NS","CONNPLEX.NS","PATELENG.NS","SWSOLAR.NS","CRAFTSMAN.NS","GIPCL.NS",
    "MOBIKWIK.NS","DBL.NS","UTTAMSUGAR.NS","PANACEABIO.NS","ENIL.NS","MVGJL.NS","CERA.NS","HITECH.NS","BLIL.NS","BHARATSE.NS",
    "FORCEMOT.NS","SHINDL.NS","LMW.NS","TATVA.NS","MAFATIND.NS","FACT.NS","TRENT.NS","OLAELEC.NS","OMAXE.NS","PARACABLES.NS",
    "RAJPALAYAM.NS","SYMPHONY.NS","BANARISUG.NS","ZYDUSLIFE.NS","HINDUNILVR.NS","BOSCH_HCIL.NS","TI.NS","REPCOHOME.NS","AJANTPHARM.NS","SRM.NS",
    "GODREJIND.NS","AIAENG.NS","3BBLACKBIO.NS","KPRMILL.NS","ADOR.NS","ESSARSHPNG.NS","CAPITALSFB.NS","SYNCOMF.NS","MEESHO.NS","CREDITACC.NS",
    "GRASIM.NS","SARLAPOLY.NS","CHEMFAB.NS","PRABHAPP.E1.NS","PRADPME.NS","ALKEM.NS","JSLL.NS","AVANTEL.NS","OCCLLTD.NS","HONDAPOWER.NS",
    "BALMLAWRIE.NS","LT.NS","AURUM.NS","MASFIN.NS","WOCKPHARMA.NS","AEGISLOG.NS","MMTC.NS","KAMAHOLD.NS","CRISIL.NS","LAURUSLABS.NS",
    "HAWKINCOOK.NS","KIRLFER.NS","SHRIRAMPPS.NS","HAL.NS","KLBRENG_B.NS","PRSMJOHNSN.NS","FMGOETZE.NS","LINC.NS","ANDHRAPAP.NS","EMBASSY.RR.NS",
    "NELCO.NS","JAYAGROGN.NS","GPTHEALTH.NS","BANSALWIRE.NS","EVEREADY.NS","NESCO.NS","METROPOLIS.NS","ICEMAKE.NS","JKCEMENT.NS","PRECAM.NS",
    "ONEPOINT.NS","MINDSPACE.RR.NS","BIRET.RR.NS","ONESOURCE.NS","IBULLSLTD.NS","NAZARA.NS","SOBHA.NS","INDUSTOWER.NS","BOROSCI.NS","MAITHANALL.NS",
    "INDNIPPON.NS","TPLPLASTEH.NS","GILLETTE.NS","GOODYEAR.NS","KMEW.NS","EPIGRAL.NS","RML.NS","TEXINFRA.NS","NIBE.NS","PRIMO.NS",
    "ORIENTHOT.NS","GLAXO.NS","SAMMAANCAP.NS","GATEWAY.NS","SUMEETINDS.NS","KRISHIVAL.NS","MONARCH.NS","SEJALLTD.NS","DAVANGERE.NS","RIIL.NS",
    "EXIDEIND.NS","DISAQ.NS","BEML.NS","IREDA.NS","ARE&M.NS","PFIZER.NS","INFOBEAN.NS","KICL.NS","TRIDENT.NS","KCP.NS",
    "ELECTHERM.NS","PCBL.NS","OSELDEVICE.NS","MOTISONS.NS","TIMETECHNO.NS","DEEPAKNTR.NS","IOB.NS","MEDANTA.NS","INSECTICID.NS","KKCL.NS",
    "UNIVCABLES.NS","RAJRILTD.NS","SIMPLEXINF.NS","SRHHYPOLTD.NS","HLVLTD.NS","PETRONET.NS","ITI.NS","ARMANFIN.NS","EICHERMOT.NS","INVPRECQ.NS",
    "FEDDERSHOL.NS","JAMNAAUTO.NS","LUMAXIND.NS","FIEMIND.NS","JASH.NS","ALKYLAMINE.NS","PGEL.NS","SHREEPUSHK.NS","CONCOR.NS","ICICIBANK.NS",
    "BLUEDART.NS","DISHTV.NS","ICIL.NS","LGBBROSLTD.NS","PANSARI.NS","BLKASHYAP.NS","TATACONSUM.NS","IMPAL.NS","GNFC.NS","SOTL.NS",
    "QUESS.NS","PGIL.NS","ANUP.NS","ONMOBILE.NS","INDGN.NS","GAIL.NS","MAXHEALTH.NS","ALLDIGI.NS","CENTRALBK.NS","VERANDA.NS",
    "TAALTECH.NS","VADILALIND.NS","CAMPUS.NS","HTMEDIA.NS","INDIACEM.NS","ARSSBL.NS","MFSL.NS","BAJAJINDEF.NS","RUPA.NS","AKCAPIT.NS",
    "STERTOOLS.NS","MONOLITH.NS","SCILAL.NS","BSHSL.NS","PIIND.NS","LICI.NS","SHRIRAMFIN.NS","RAJRATAN.NS","CUB.NS","SUNDROP.NS",
    "AARTIPHARM.NS","TECHNVISN.NS","PPLPHARMA.NS","DREDGECORP.NS","HONAUT.NS","NEULANDLAB.NS","CASTROLIND.NS","LALPATHLAB.NS","PHOENIXLTD.NS","TATACAP.NS",
    "ASIANTILES.NS","CONTROLPR.NS","KRBL.NS","VRLLOG.NS","ARIS.NS","TMPV.NS","CANFINHOME.NS","GNRL.NS","ABCAPITAL.NS","UNITDSPR.NS",
    "ZEEMEDIA.NS","VHL.NS","PLATIND.NS","VISAKAIND.NS","GMRP&UI.NS","STOVEKRAFT.NS","ACE.NS","BAJAJHFL.NS","BALKRISIND.NS","INDIAMART.NS",
    "NACLIND.NS","GSFC.NS","SMLMAH.NS","DEEPAKFERT.NS","GALAPREC.NS","CREST.NS","NDRAUTO.NS","MAMATA.NS","ULTRAMAR.NS","GOKEX.NS",
    "KRT.RR.NS","KSCL.NS","MAANALU.NS","SICALLOG.NS","3MINDIA.NS","BHAGERIA.NS","SANDESH.NS","KOLTEPATIL.NS","VIKRAMSOLR.NS","PARKHOTELS.NS",
    "FRONTSP.NS","THELEELA.NS","MSPL.NS","UTKARSHBNK.NS","JAYKAY.NS","KALPATARU.NS","CENTURYPLY.NS","C2C.NS","LEMERITE.NS","STCINDIA.NS",
    "FOSECOIND.NS","FIVESTAR.NS","DIXON.NS","INDIAGLYCO.NS","IRISDOREME.NS","MANAPPURAM.NS","BALAJITELE.NS","CAPLIPOINT.NS","DCMSHRIRAM.NS","BDL.NS",
    "CYIENTDLM.NS","VAIBHAVGBL.NS","SPECTRUM.NS","ASTRAZEN.NS","HEMIPROP.NS","ORIANA.NS","BORORENEW.NS","BRITANNIA.NS","RALLIS.NS","FCL.NS",
    "KPL.NS","PIDILITIND.NS","SUDARSCHEM.NS","VINDHYATEL.NS","SHREECEM.NS","GUJGASLTD.NS","JINDRILL.NS","QUADFUTURE.NS","TVSMOTOR.NS","OMINFRAL.NS",
    "BUTTERFLY.NS","PFS.NS","NH.NS","SETL.NS","BAJFINANCE.NS","ASHOKLEY.NS","GEECEE.NS","HNDFDS.NS","IEX.NS","MALLCOM.NS",
    "IFGLEXPOR.NS","SUPRIYA.NS","ELCIDIN.NS","PANAMAPET.NS","FLUOROCHEM.NS","TREL.NS","HUDCO.NS","LOTUSDEV.NS","THEMISMED.NS","BLUSPRING.NS",
    "GMRAIRPORT.NS","JSWDULUX.NS","SKFINDIA.NS","MICEL.NS","ADVANIHOTR.NS","BAJAJST.NS","JSL.NS","RELTD.NS","REMUS.NS","PACEDIGITK.NS",
    "VMM.NS","GREENPLY.NS","SJS.NS","NUVAMA.NS","CEATLTD.NS","NSLNISP.NS","SALZERELEC.NS","LGHL.NS","COHANCE.NS","SAFEENTP.NS",
    "TINNARUBR.NS","FISCHER.NS","AAVAS.NS","CHAMBLFERT.NS","RAINBOW.NS","SUMICHEM.NS","JYOTHYLAB.NS","ADVANCE.NS","HGS.NS","SURAJEST.NS",
    "MOLDTKPAC.NS","ZTECH.NS","ASIANHOTNR.NS","MOTILALOFS.NS","JTEKTINDIA.NS","WEWORK.NS","BLSE.NS","ELITECON.NS","JAGRAN.NS","SHARDAMOTR.NS",
    "BIOCON.NS","MMWL.NS","YESBANK.NS","THYROCARE.NS","CANHLIFE.NS","IVALUE.NS","JMFINANCIL.NS","GKENERGY.NS","SUPREMEINF.NS","LAXMIINDIA.NS",
    "AARTIDRUGS.NS","FILATEX.NS","TARSONS.NS","HERANBA.NS","ESAFSFB.NS","INNOVANA.NS","CDSL.NS","PILANIINVS.NS","CHEMPLASTS.NS","GSPL.NS",
    "GODIGIT.NS","MUTHOOTFIN.NS","CENTENKA.NS","BASF.NS","GANDHAR.NS","ASALCBR.NS","THEINVEST.NS","KPIGREEN.NS","APTUS.NS","NBIFIN.NS",
    "EIFFL.NS","HEIDELBERG.NS","ALLTIME.NS","RAMKY.NS","ASKAUTOLTD.NS","IKS.NS","GHCL.NS","TEJASNET.NS","GREENLAM.NS","ACCELYA.NS",
    "STUDDS.NS","STEL.NS","BANCOINDIA.NS","RITES.NS","BAJAJHLDNG.NS","PSB.NS","RELIGARE.NS","SANDHAR.NS","UBL.NS","GRINFRA.NS",
    "EIHAHOTELS.NS","KAMDHENU.NS","ATL.NS","RAMCOCEM.NS","ALEMBICLTD.NS","PDMJEPAPER.NS","TVSSRICHAK.NS","IZMO.NS","STYL.NS","SASTASUNDR.NS",
    "HPL.NS","KITEX.NS","GODREJPROP.NS","ENDURANCE.NS","BANKBARODA.NS","RAIN.NS","SUBROS.NS","ALLCARGO.NS","BIKAJI.NS","DHANUKA.NS",
    "VPRPL.NS","PUNJABCHEM.NS","SUPRAJIT.NS","BRIGADE.NS","SBFC.NS","MANINFRA.NS","GLOSTERLTD.NS","POLICYBZR.NS","SCODATUBES.NS","CLEAN.NS",
    "LTF.NS","APLLTD.NS","PNB.NS","BLAL.NS","PGHL.NS","PURVA.NS","DEN.NS","DODLA.NS","ICRA.NS","CHOLAFIN.NS",
    "DALBHARAT.NS","MAXESTATES.NS","ICICIGI.NS","ANANTRAJ.NS","JARO.NS","TCIEXP.NS","ABREL.NS","MINDACORP.NS","PVP.NS","AHLUCONT.NS",
    "GREENPANEL.NS","SIYSIL.NS","INTERARCH.NS","JLHL.NS","FABTECH.NS","KWIL.NS","JINDWORLD.NS","BOROLTD.NS","ESTER.NS","CHALET.NS",
    "ABINFRA.NS","SANDUMA.NS","GARUDA.NS","JAICORPLTD.NS","PRICOLLTD.NS","INDRAMEDCO.NS","ASIANPAINT.NS","VAKRANGEE.NS","MOIL.NS","ARTEMISMED.NS",
    "SBILIFE.NS","PVSL.NS","GALAXYSURF.NS","ARVINDFASN.NS","BCG.NS","DABUR.NS","RHIM.NS","DIFFNKG.NS","GODREJCP.NS","TBZ.NS",
    "SANSTAR.NS","TTML.NS","HAVELLS.NS","TATATECH.NS","SIRCA.NS","IIFLCAPS.NS","MTNL.NS","GEOJITFSL.NS","KUANTUM.NS","RAILTEL.NS",
    "HATHWAY.NS","PPL.NS","TSFINV.NS","KILITCH.NS","AJAXENGG.NS","TASTYBITE.NS","GRANDOAK.NS","JUBLPHARMA.NS","ETERNAL.NS","TCI.NS",
    "EIHOTEL.NS","INDOCO.NS","SUNTECK.NS","UCOBANK.NS","TCPLPACK.NS","SHRINGARMS.NS","GARFIBRES.NS","IDEA.NS","LANDMARK.NS","TECHM.NS",
    "PNBGILTS.NS","RPGLIFE.NS","DBREALTY.NS","AMNPLST.NS","HITECHGEAR.NS","RCF.NS","VMART.NS","CANBK.NS","LXCHEM.NS","JKIL.NS",
    "ABDL.NS","GOPAL.NS","COROMANDEL.NS","AHCL.NS","KFINTECH.NS","DATAMATICS.NS","NSIL.NS","LAOPALA.NS","ESCORTS.NS","RADHIKAJWE.NS",
    "BIRLANU.NS","AGI.NS","DOLLAR.NS","CANTABIL.NS","RELIANCE.NS","UNOMINDA.NS","INDHOTEL.NS","MBEL.NS","TITAGARH.NS","ABBOTINDIA.NS",
    "HDBFS.NS","WENDT.NS","EUROPRATIK.NS","CMSINFO.NS","GICHSGFIN.NS","TTKHLTCARE.NS","HEROMOTOCO.NS","AMRUTANJAN.NS","DECCANCE.NS","HARIOMPIPE.NS",
    "VARROC.NS","ERIS.NS","DOMS.NS","MONTECARLO.NS","IGARASHI.NS","SFL.NS","PRABHA.NS","PRESTIGE.NS","TATACOMM.NS","PNCINFRA.NS",
    "PROSTARM.NS","ATLPP.E1.NS","PAYTM.NS","INDIGO.NS","BAJAJFINSV.NS","VINCOFE.NS","VIDHIING.NS","MAHSCOOTER.NS","MAXIND.NS","HCG.NS",
    "AGARWALEYE.NS","RTNINDIA.NS","GRAVITA.NS","METROBRAND.NS","SANGHVIMOV.NS","MANAKCOAT.NS","SASKEN.NS","NUCLEUS.NS","INDOAMIN.NS","GREAVESCOT.NS",
    "CSBBANK.NS","SKFINDUS.NS","UFLEX.NS","ORIENTCEM.NS","BIRLACORPN.NS","VASCONEQ.NS","BHARTIARTL.NS","ETHOSLTD.NS","IOC.NS","360ONE.NS",
    "SACHEEROME.NS","PSPPROJECT.NS","EMUDHRA.NS","GANESHCP.NS","VEEDOL.NS","EMAMILTD.NS","ROTO.NS","GPPL.NS","RAMCOIND.NS","GUFICBIO.NS",
    "MADRASFERT.NS","BLS.NS","SURYAROSNI.NS","SAMHI.NS","JUBLFOOD.NS","INDOSTAR.NS","CAPILLARY.NS","MANALIPETC.NS","SUNDARMFIN.NS","IPL.NS",
    "ALOKINDS.NS","NCLIND.NS","SUNDRMFAST.NS","INDOBORAX.NS","ALICON.NS","IRCON.NS","FDC.NS","CIPLA.NS","NPST.NS","HBLENGINE.NS",
    "PTCIL.NS","RNFI.NS","WCIL.NS","TEGA.NS","AWL.NS","ASAHIINDIA.NS","NITCO.NS","AFCONS.NS","DOLPHIN.NS","PINELABS.NS",
    "DVL.NS","SVLL.NS","DIAMONDYD.NS","POLYMED.NS","KOTAKBANK.NS","BOMDYEING.NS","ARKADE.NS","SUMMITSEC.NS","FIRSTCRY.NS","DOLATALGO.NS",
    "INOXGREEN.NS","MRF.NS","BLACKBUCK.NS","CRAMC.NS","RVNL.NS","IGL.NS","SAGCEM.NS","POCL.NS","SHAREINDIA.NS","SMARTWORKS.NS",
    "BERGEPAINT.NS","POONAWALLA.NS","BECTORFOOD.NS","SSEGL.NS","UTIAMC.NS","DLF.NS","TNPETRO.NS","NDTV.NS","RATEGAIN.NS","APOLLOTYRE.NS",
    "BSOFT.NS","SOLARA.NS","KELLTONTEC.NS","SUBEXLTD.NS","JWL.NS","CHOLAHLDNG.NS","OSWALGREEN.NS","JIOFIN.NS","JISLDVREQS.NS","MSTCLTD.NS",
    "KANSAINER.NS","ZOTA.NS","SALASAR.NS","BETA.NS","MAHLIFE.NS","MARATHON.NS","DDEVPLSTIK.NS","SANOFI.NS","FLYSBS.NS","GUJTHEM.NS",
    "KALYANKJIL.NS","CENTRUM.NS","AURIONPRO.NS","JKLAKSHMI.NS","ELDEHSG.NS","EXPLEOSOL.NS","PATANJALI.NS","CEMPRO.NS","WESTLIFE.NS","BFUTILITIE.NS",
    "HUHTAMAKI.NS","CCAVENUE.NS","WSI.NS","TIRUMALCHM.NS","ACL.NS","ONWARDTEC.NS","BAJAJELEC.NS","HUBTOWN.NS","CAMLINFINE.NS","IRFC.NS",
    "UNICHEMLAB.NS","GANESHHOU.NS","DBCORP.NS","MPSLTD.NS","NFL.NS","WAAREEINDO.NS","VSTTILLERS.NS","HMAAGRO.NS","GFLLIMITED.NS","V2RETAIL.NS",
    "RICOAUTO.NS","OPTIEMUS.NS","M&M.NS","20MICRONS.NS","TARACHAND.NS","KRSNAA.NS","BLUEJET.NS","ORISSAMINE.NS","DENTA.NS","RPOWER.NS",
    "PENIND.NS","SPIC.NS","ABFRL.NS","STALLION.NS","BHARTIHEXA.NS","XCHANGING.NS","SDBL.NS","LODHA.NS","TTKPRESTIG.NS","OSWALAGRO.NS",
    "INOXWIND.NS","UNIECOM.NS","ACC.NS","SEPC.NS","SHK.NS","HIKAL.NS","CNL.NS","EMSLIMITED.NS","GULFOILLUB.NS","VINATIORGA.NS",
    "UNITECH.NS","AMBUJACEM.NS","ROHLTD.NS","RANEHOLDIN.NS","RAYMONDREL.NS","UDS.NS","SRF.NS","NUVOCO.NS","HINDWAREAP.NS","EIDPARRY.NS",
    "JUNIPER.NS","INDIQUBE.NS","BGRENERGY.NS","GMMPFAUDLR.NS","ZUARIIND.NS","MASTEK.NS","TVTODAY.NS","SPANDANA.NS","MSUMI.NS","ABLBL.NS",
    "CONCORDBIO.NS","MOL.NS","PARADEEP.NS","INDORAMA.NS","ROSSARI.NS","ASHOKA.NS","SULA.NS","ARIHANTSUP.NS","SHREDIGCEM.NS","NILASPACES.NS",
    "CHANDAN.NS","MPHASIS.NS","CHOICEIN.NS","GMBREW.NS","UPL.NS","ELLEN.NS","DCW.NS","BALUFORGE.NS","NETWORK18.NS","PAUSHAKLTD.NS",
    "RGL.NS","PWL.NS","MAHASTEEL.NS","IDFCFIRSTB.NS","EUREKAFORB.NS","HAPPSTMNDS.NS","MATRIMONY.NS","MEIL.NS","HGINFRA.NS","HYUNDAI.NS",
    "ITCHOTELS.NS","JKTYRE.NS","IKIO.NS","LTTS.NS","AFFLE.NS","SHALBY.NS","VENTIVE.NS","BBTC.NS","ARIHANTCAP.NS","NIITMTS.NS",
    "KNRCON.NS","AEGISVOPAK.NS","BPCL.NS","IRCTC.NS","REPRO.NS","MHRIL.NS","REDINGTON.NS","SAGILITY.NS","HERITGFOOD.NS","CHEMCON.NS",
    "RESPONIND.NS","TEAMLEASE.NS","MARUTI.NS","HDFCBANK.NS","CIFL.NS","MANBA.NS","HDFCLIFE.NS","PARAGMILK.NS","AIIL.NS","ALGOQUANT.NS",
    "TARC.NS","EMBDL.NS","SKMEGGPROD.NS","SHAKTIPUMP.NS","PGHH.NS","YUKEN.NS","TATAELXSI.NS","KODYTECH.NS","OSWALPUMPS.NS","EMKAY.NS",
    "RITCO.NS","JUBLCPL.NS","WAKEFIT.NS","NIITLTD.NS","INTELLECT.NS","RAYMONDLSL.NS","JISLJALEQS.NS","MUFTI.NS","LAXMIDENTL.NS","INDIANHUME.NS",
    "DPABHUSHAN.NS","HIMATSEIDE.NS","VLSFINANCE.NS","M&MFIN.NS","CYIENT.NS","CELLO.NS","ICICIPRULI.NS","VIPIND.NS","SSFLPP.E1.NS","RUSHIL.NS",
    "KEC.NS","TIL.NS","IRIS.NS","GODFRYPHLP.NS","NBCC.NS","BATAINDIA.NS","ADSL.NS","SIGNATURE.NS","JYOTICNC.NS","SHOPERSTOP.NS",
    "BAJAJHCARE.NS","PERSISTENT.NS","TEXRAIL.NS","WIPRO.NS","FAIRCHEMOR.NS","INDIGOPNTS.NS","DAMCAPITAL.NS","TBOTEK.NS","TCS.NS","DEVYANI.NS",
    "ITC.NS","PDSL.NS","CRIZAC.NS","HINDPETRO.NS","MANYAVAR.NS","ORCHPHARMA.NS","ZENSARTECH.NS","TAJGVK.NS","SBICARD.NS","EVERESTIND.NS",
    "HLEGLAS.NS","RELAXO.NS","SUDARCOLOR.NS","IFBIND.NS","MEDIASSIST.NS","NAUKRI.NS","DHUNINV.NS","VIMTALABS.NS","BHARATCOAL.NS","RUSTOMJEE.NS",
    "UNIENTER.NS","ELIN.NS","ROUTE.NS","ZUARI.NS","SOLARWORLD.NS","JINDALPHOT.NS","IDBI.NS","RAMCOSYS.NS","TCC.NS","CSLFINANCE.NS",
    "CEWATER.NS","DCAL.NS","LEMONTREE.NS","RPEL.NS","HCLTECH.NS","MIDWESTLTD.NS","EPACKPEB.NS","SAURASHCEM.NS","JUSTDIAL.NS","COFFEEDAY.NS",
    "PENINLAND.NS","ASHAPURMIN.NS","VIKRAN.NS","STANLEY.NS","CIGNITITEC.NS","LTM.NS","WEL.NS","AWFIS.NS","DIGITIDE.NS","ZAGGLE.NS",
    "COFORGE.NS","SWANCORP.NS","SMCGLOBAL.NS","FINKURVE.NS","IIFL.NS","SWIGGY.NS","BESTAGRO.NS","DENTALKART.NS","INFY.NS","SAKSOFT.NS",
    "DCMSRIND.NS","PROTEAN.NS","SONATSOFTW.NS","VISASTEEL.NS","KAMATHOTEL.NS","BASILIC.NS","MVKAGRO.NS","ORIENTTECH.NS","RAJESHEXPO.NS","KHAICHEM.NS",
    "ECOSMOBLTY.NS","GTPL.NS","INDOFARM.NS","ADVENTHTL.NS","SHREERAMA.NS","AMIRCHAND.NS","SYNGENE.NS","SAPPHIRE.NS","SAFARI.NS","IXIGO.NS",
    "GOCOLORS.NS","FOCE.NS","RSYSTEMS.NS","KALAMANDIR.NS","THOMASCOOK.NS","SIGACHI.NS","AJMERA.NS","TAC.NS","LATENTVIEW.NS","EFCIL.NS",
    "MASTERTR.NS","JSWHL.NS","IFBAGRO.NS","QUICKHEAL.NS","YATRA.NS","INNOVISION.NS","FSL.NS","UGROCAP.NS","BHARATRAS.NS","KPITTECH.NS",
    "RAMASTEEL.NS","ECLERX.NS","GENESYS.NS","BIGBLOC.NS","AGARIND.NS","CARTRADE.NS","HEXT.NS","ABCOTS.NS","NEWGEN.NS","SYSTMTXC.NS",
    "KIRIINDUS.NS","MAPMYINDIA.NS","FINOPB.NS","RELINFRA.NS","RMDRIP.NS","AQYLON.NS",
]

SECTOR_MAP = {
    "RELIANCE.NS":"Energy","TCS.NS":"IT","HDFCBANK.NS":"Banking","INFY.NS":"IT",
    "ICICIBANK.NS":"Banking","HINDUNILVR.NS":"FMCG","SBIN.NS":"Banking",
    "BAJFINANCE.NS":"Finance","BHARTIARTL.NS":"Telecom","KOTAKBANK.NS":"Banking",
    "AXISBANK.NS":"Banking","LT.NS":"Infra","HCLTECH.NS":"IT","ASIANPAINT.NS":"Consumer",
    "WIPRO.NS":"IT","MARUTI.NS":"Auto","SUNPHARMA.NS":"Pharma","TITAN.NS":"Consumer",
    "ULTRACEMCO.NS":"Cement","NESTLEIND.NS":"FMCG","ONGC.NS":"Energy",
    "POWERGRID.NS":"Energy","NTPC.NS":"Energy","TECHM.NS":"IT","BAJAJFINSV.NS":"Finance",
    "TATAMOTORS.NS":"Auto","DRREDDY.NS":"Pharma","DIVISLAB.NS":"Pharma",
    "CIPLA.NS":"Pharma","ADANIPORTS.NS":"Infra","COALINDIA.NS":"Energy",
    "GRASIM.NS":"Cement","HINDALCO.NS":"Metal","JSWSTEEL.NS":"Metal",
    "TATASTEEL.NS":"Metal","BPCL.NS":"Energy","IOC.NS":"Energy","HEROMOTOCO.NS":"Auto",
    "EICHERMOT.NS":"Auto","BAJAJ-AUTO.NS":"Auto","BRITANNIA.NS":"FMCG",
    "DABUR.NS":"FMCG","MARICO.NS":"FMCG","COLPAL.NS":"FMCG","GODREJCP.NS":"FMCG",
    "PIDILITIND.NS":"Consumer","BERGEPAINT.NS":"Consumer","HAVELLS.NS":"Consumer",
    "VOLTAS.NS":"Consumer","ITC.NS":"FMCG","PERSISTENT.NS":"IT","MPHASIS.NS":"IT",
    "LTIM.NS":"IT","COFORGE.NS":"IT","ZOMATO.NS":"Consumer","IRCTC.NS":"Consumer",
    "INDHOTEL.NS":"Consumer","RVNL.NS":"Infra","IRFC.NS":"Finance","RECLTD.NS":"Finance",
    "PFC.NS":"Finance","BANKBARODA.NS":"Banking","CANBK.NS":"Banking","PNB.NS":"Banking",
    "FEDERALBNK.NS":"Banking","IDFCFIRSTB.NS":"Banking","INDUSINDBK.NS":"Banking",
    "AUBANK.NS":"Banking","CHOLAFIN.NS":"Finance","MUTHOOTFIN.NS":"Finance",
    "APOLLOHOSP.NS":"Pharma","FORTIS.NS":"Pharma","AUROPHARMA.NS":"Pharma",
    "LUPIN.NS":"Pharma","TORNTPHARM.NS":"Pharma","TATAPOWER.NS":"Energy",
    "ADANIGREEN.NS":"Energy","NAUKRI.NS":"IT","INDIGO.NS":"Consumer","OFSS.NS":"IT",
    "DIXON.NS":"Consumer","TATACONSUM.NS":"FMCG","MOTHERSON.NS":"Auto",
    "BALKRISIND.NS":"Auto","DMART.NS":"Consumer","ABCAPITAL.NS":"Finance",
    "MFSL.NS":"Finance","SBICARD.NS":"Finance","HDFCAMC.NS":"Finance","NIPPONLIFE.NS":"Finance",
    "ANGELONE.NS":"Finance","ICICIPRULI.NS":"Finance","HDFCLIFE.NS":"Finance",
    "360ONE.NS":"Finance","MOTILALOFS.NS":"Finance","ICICIGI.NS":"Finance",
    "STARHEALTH.NS":"Finance","NUVAMA.NS":"Finance",
    "HAL.NS":"Defence","BEL.NS":"Defence","BHEL.NS":"Infra","COCHINSHIP.NS":"Defence",
    "CGPOWER.NS":"CapGoods","SIEMENS.NS":"CapGoods","ABB.NS":"CapGoods",
    "CUMMINSIND.NS":"CapGoods","THERMAX.NS":"CapGoods",
    "TRENT.NS":"Consumer","KALYANKJIL.NS":"Consumer","VBL.NS":"FMCG",
    "KPITTECH.NS":"IT","SUPREMEIND.NS":"Consumer","GRINDWELL.NS":"CapGoods",
    "TIMKEN.NS":"CapGoods","SCHAEFFLER.NS":"CapGoods",
}

# Sector colors retuned to gold/dark complementary palette
SECTOR_COLORS = {
    "Banking":"#4A7A8B", "IT":"#8E6FD8", "FMCG":"#D4A442", "Finance":"#7A8B3F",
    "Energy":"#E74C3C", "Infra":"#5A7A8B", "Auto":"#C8922A", "Pharma":"#B85A8B",
    "Consumer":"#9DA856", "Metal":"#7A7060", "Cement":"#A8841E", "Telecom":"#5DA9C7",
    "Defence":"#7257B3", "CapGoods":"#7A8B5A",
}


# ═══════════════════════════════════════════════════════════════
#  CMT LOGIC (verbatim from nse-swing.py)
# ═══════════════════════════════════════════════════════════════
def calculate_atr(df, period=14):
    hl = df['High'] - df['Low']
    hc = (df['High'] - df['Close'].shift()).abs()
    lc = (df['Low']  - df['Close'].shift()).abs()
    tr = pd.concat([hl, hc, lc], axis=1).max(axis=1)
    return float(tr.rolling(period).mean().iloc[-1])


def calculate_adx(df, period=14):
    h, l, c = df['High'], df['Low'], df['Close']
    plus_dm  = h.diff().where((h.diff() > -l.diff()) & (h.diff() > 0), 0)
    minus_dm = (-l.diff()).where((-l.diff() > h.diff()) & (-l.diff() > 0), 0)
    tr = pd.concat([h - l, (h - c.shift()).abs(), (l - c.shift()).abs()], axis=1).max(axis=1)
    atr_s = tr.rolling(period).mean()
    pd_  = 100 * plus_dm.rolling(period).mean()  / atr_s
    md_  = 100 * minus_dm.rolling(period).mean() / atr_s
    dx   = 100 * (pd_ - md_).abs() / (pd_ + md_ + 1e-9)
    adx  = dx.rolling(period).mean()
    return float(adx.iloc[-1]) if not adx.empty else 0


def find_swings(df, lookback=10):
    highs, lows, n = df['High'].values, df['Low'].values, len(df)
    sh, sl = [], []
    for i in range(lookback, n - lookback):
        if highs[i] == max(highs[i - lookback: i + lookback + 1]):
            sh.append((df.index[i], round(float(highs[i]), 2)))
        if lows[i] == min(lows[i - lookback: i + lookback + 1]):
            sl.append((df.index[i], round(float(lows[i]), 2)))
    return sh, sl


@st.cache_data(ttl=1800, show_spinner=False)
def get_market_regime():
    try:
        import yfinance as yf
        n = yf.Ticker("^NSEI").history(period="6mo")
        if n.empty or len(n) < 50:
            return True, 0
        close = float(n['Close'].iloc[-1])
        ma50  = float(n['Close'].iloc[-50:].mean())
        return close > ma50, round((close - ma50) / ma50 * 100, 2)
    except Exception:
        return True, 0


@st.cache_data(ttl=1800, show_spinner=False)
def get_nifty_return(period_days=63):
    try:
        import yfinance as yf
        n = yf.Ticker("^NSEI").history(period="1y")
        if n.empty or len(n) < period_days:
            return 0
        return float((n['Close'].iloc[-1] / n['Close'].iloc[-period_days] - 1) * 100)
    except Exception:
        return 0


def check_rs(df, nifty_ret, period_days=63):
    if len(df) < period_days:
        return False, 0, 0
    ret = float((df['Close'].iloc[-1] / df['Close'].iloc[-period_days] - 1) * 100)
    return ret > nifty_ret, round(ret, 2), round(ret - nifty_ret, 2)


def wyckoff_check(df, sh_idx, lo_idx):
    if lo_idx <= sh_idx:
        return True, 1.0
    seg = df.iloc[sh_idx: lo_idx + 1]
    if len(seg) < 3:
        return True, 1.0
    up = seg[seg['Close'] > seg['Open']]['Volume'].sum()
    dn = seg[seg['Close'] < seg['Open']]['Volume'].sum()
    if dn == 0:
        return True, 2.0
    return (up / dn) >= 0.6, round(float(up / dn), 2)


def tight_base(df, period=15, max_sd_pct=4.0):
    if len(df) < period:
        return True, 0
    c = df['Close'].iloc[-period:]
    sd = float(c.std() / c.mean() * 100)
    return sd <= max_sd_pct, round(sd, 2)


def find_valid_resistance(df, swing_highs, threshold_atr_mult=1.5,
                           min_pullback_pct=5.0, min_sh_age=12, min_pb_age=10):
    if not swing_highs:
        return None
    close   = float(df['Close'].iloc[-1])
    closes  = df['Close'].values
    highs_a = df['High'].values
    lows_a  = df['Low'].values
    n       = len(df)

    if n >= 50 and close < float(df['Close'].iloc[-50:].mean()) * 0.97:
        return None

    atr = calculate_atr(df)
    if atr == 0 or np.isnan(atr):
        return None

    for sh_date, sh_price in reversed(swing_highs):
        if sh_price <= close:
            continue
        try:
            bar_idx = df.index.get_loc(sh_date)
        except Exception:
            continue
        if (n - 1 - bar_idx) < min_sh_age:
            continue

        post_lows = lows_a[bar_idx + 1:]
        if len(post_lows) == 0:
            continue
        lo_rel = int(np.argmin(post_lows))
        lo_abs = bar_idx + 1 + lo_rel
        lo_val = float(post_lows[lo_rel])
        pb_pct = (sh_price - lo_val) / sh_price * 100
        if pb_pct < min_pullback_pct:
            continue

        if (n - 1 - lo_abs) < min_pb_age:
            continue

        if lo_abs < n - 1:
            hs = highs_a[lo_abs: n - 1]
            if len(hs) > 0 and float(hs.max()) > sh_price * 1.002:
                continue

        if int(np.sum(closes > sh_price * 1.002)) / n > 0.10:
            continue

        win_len = min(120, bar_idx)
        if win_len > 20:
            pre = highs_a[bar_idx - win_len: bar_idx]
            if len(pre) > 0 and float(pre.max()) > sh_price:
                continue

        gap_pts = sh_price - close
        gap_atr = round(gap_pts / atr, 2)
        if gap_atr > threshold_atr_mult:
            continue

        base_ok, base_sd = tight_base(df)
        if not base_ok:
            continue

        wy_ok, wy_ratio = wyckoff_check(df, bar_idx, lo_abs)

        tier = "HOT" if gap_atr <= 0.5 else "WARM" if gap_atr <= 1.0 else "CLOSE"

        return {
            "price": sh_price, "date": sh_date,
            "gap_pct": round(gap_pts/sh_price*100, 2),
            "gap_atr": gap_atr, "tier": tier,
            "pullback_pct": round(pb_pct, 2),
            "pullback_low": round(lo_val, 2),
            "base_sd_pct": base_sd,
            "wyckoff_ok": wy_ok, "wyckoff_ratio": wy_ratio,
            "atr": round(atr, 2),
        }
    return None


@st.cache_data(ttl=1800, show_spinner=False)
def batch_download_prices():
    """
    Download 2Y daily OHLCV for the entire Nifty 500 in ONE API call.
    yf.download() is ~10x faster than 500 individual Ticker.history() calls.
    Cached for 30 min — shared between approaching + breakout scans.
    """
    import yfinance as yf
    data = yf.download(
        WATCHLIST,
        period="2y",
        interval="1d",
        auto_adjust=True,
        progress=False,
        group_by="ticker",
        threads=True,        # yfinance internal threading
    )
    return data


@st.cache_data(ttl=1800, show_spinner=False)
def batch_download_mcap():
    """
    Fetch market caps for all tickers in parallel using ThreadPoolExecutor.
    Returns dict: {sym: mcap_cr}
    """
    import yfinance as yf
    from concurrent.futures import ThreadPoolExecutor, as_completed

    def _get_mcap(sym):
        try:
            fi = yf.Ticker(sym).fast_info
            return sym, (getattr(fi, "market_cap", 0) or 0) / 1e7
        except Exception:
            return sym, 0

    mcap_map = {}
    with ThreadPoolExecutor(max_workers=30) as ex:
        futures = {ex.submit(_get_mcap, sym): sym for sym in WATCHLIST}
        for fut in as_completed(futures):
            sym, mcap = fut.result()
            mcap_map[sym] = mcap
    return mcap_map


def _extract_df(all_data, sym):
    """Pull a single ticker's DataFrame out of the batch download result."""
    try:
        if sym in all_data.columns.get_level_values(0):
            df = all_data[sym][['Open','High','Low','Close','Volume']].copy()
            df = df.dropna(subset=['Close'])
            return df if len(df) >= 80 else None
        return None
    except Exception:
        return None


@st.cache_data(ttl=900, show_spinner=False)
def run_approaching(lookback, min_mcap, threshold_atr):
    risk_on, _ = get_market_regime()
    nifty_ret  = get_nifty_return(63)

    all_data = batch_download_prices()
    mcap_map = batch_download_mcap()

    results = []
    for sym in WATCHLIST:
        try:
            mcap_cr = mcap_map.get(sym, 0)
            if mcap_cr < min_mcap:
                continue
            df = _extract_df(all_data, sym)
            if df is None:
                continue
            rs_ok, stock_ret, rs_diff = check_rs(df, nifty_ret)
            if not rs_ok:
                continue
            sh, sl = find_swings(df, lookback)
            r = find_valid_resistance(df, sh, threshold_atr_mult=threshold_atr)
            if not r:
                continue
            close   = round(float(df['Close'].iloc[-1]), 2)
            prev    = round(float(df['Close'].iloc[-2]), 2)
            day_chg = round((close - prev) / prev * 100, 2)
            vn = float(df['Volume'].iloc[-1])
            va = float(df['Volume'].iloc[-21:-1].mean())
            vr = round(vn / va, 2) if va > 0 else 0
            adx = round(calculate_adx(df), 1)
            results.append({
                "symbol": sym.replace(".NS", ""), "full_sym": sym,
                "close": close, "day_chg": day_chg,
                "swing_high": r["price"], "sh_date": r["date"].strftime("%d %b '%y"),
                "swing_low": sl[-1][1] if sl else None,
                "gap_pct": r["gap_pct"], "gap_atr": r["gap_atr"], "tier": r["tier"],
                "pullback": r["pullback_pct"], "base_sd": r["base_sd_pct"],
                "wyckoff_ok": r["wyckoff_ok"], "wyckoff_ratio": r["wyckoff_ratio"],
                "vol_ratio": vr, "adx": adx,
                "rs_diff": rs_diff, "stock_ret": stock_ret,
                "mcap_cr": round(mcap_cr), "sector": SECTOR_MAP.get(sym, "Other"),
                "sh_list": [(d.strftime("%Y-%m-%d"), p) for d, p in sh[-8:]],
                "sl_list": [(d.strftime("%Y-%m-%d"), p) for d, p in sl[-8:]],
            })
        except Exception:
            continue
    order = {"HOT": 0, "WARM": 1, "CLOSE": 2}
    return sorted(results, key=lambda x: (order[x["tier"]], x["gap_atr"])), risk_on


@st.cache_data(ttl=900, show_spinner=False)
def run_breakouts(lookback, min_mcap, days_back=5):
    risk_on, _ = get_market_regime()
    nifty_ret  = get_nifty_return(63)

    all_data = batch_download_prices()
    mcap_map = batch_download_mcap()

    results = []
    for sym in WATCHLIST:
        try:
            mcap_cr = mcap_map.get(sym, 0)
            if mcap_cr < min_mcap:
                continue
            df = _extract_df(all_data, sym)
            if df is None:
                continue
            rs_ok, stock_ret, rs_diff = check_rs(df, nifty_ret)
            if not rs_ok:
                continue
            sh, sl = find_swings(df, lookback)
            n      = len(df)
            closes = df['Close'].values
            vols   = df['Volume'].values

            bo_days = None; bo_level = None; bo_date = None; conf = None
            for days_ago in range(1, days_back + 1):
                cidx    = n - days_ago
                c_close = float(closes[cidx])
                p_close = float(closes[cidx - 1])
                df_s    = df.iloc[:cidx]
                sh_s, _ = find_swings(df_s, lookback)
                v       = find_valid_resistance(df_s, sh_s, threshold_atr_mult=10.0)
                if not v:
                    continue
                res = v["price"]
                if c_close > res and p_close <= res:
                    next_idx = cidx + 1
                    got = None
                    if next_idx < n and float(closes[next_idx]) > res:
                        got = "2-candle"
                    else:
                        va_ = float(vols[max(0, cidx - 20):cidx].mean())
                        if va_ > 0 and float(vols[cidx]) / va_ >= 1.5:
                            got = "volume"
                    if got is None and days_ago == 1:
                        got = "pending"
                    elif got is None:
                        continue
                    bo_days = days_ago; bo_level = res
                    bo_date = v["date"]; conf = got
                    break
            if bo_days is None:
                continue

            close   = round(float(closes[-1]), 2)
            prev    = round(float(closes[-2]), 2)
            day_chg = round((close - prev) / prev * 100, 2)
            bo_pct  = round((close - bo_level) / bo_level * 100, 2)
            lbl     = "TODAY" if bo_days == 1 else f"{bo_days}D AGO"
            adx     = round(calculate_adx(df), 1)
            vn = float(df['Volume'].iloc[-1])
            va = float(df['Volume'].iloc[-21:-1].mean())
            vr = round(vn / va, 2) if va > 0 else 0

            results.append({
                "symbol": sym.replace(".NS", ""), "full_sym": sym,
                "close": close, "day_chg": day_chg,
                "broken_sh": bo_level,
                "sh_date": bo_date.strftime("%d %b '%y") if bo_date else "—",
                "bo_pct": bo_pct, "days_ago": bo_days, "label": lbl,
                "confirmation": conf,
                "swing_low": sl[-1][1] if sl else None,
                "vol_ratio": vr, "adx": adx, "rs_diff": rs_diff,
                "mcap_cr": round(mcap_cr), "sector": SECTOR_MAP.get(sym, "Other"),
                "sh_list": [(d.strftime("%Y-%m-%d"), p) for d, p in sh[-8:]],
                "sl_list": [(d.strftime("%Y-%m-%d"), p) for d, p in sl[-8:]],
            })
        except Exception:
            continue
    return sorted(results, key=lambda x: (x["days_ago"], -x["bo_pct"])), risk_on



# ═══════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown(f"""
    <div style='padding:12px 0 16px; border-bottom:1px solid {RH_BORDER}; margin-bottom:14px;'>
        <div style='font-family:Fraunces,serif; font-size:1.2rem; font-weight:700;
                    color:{RH_GOLD_LIGHT}; letter-spacing:0.04em;'>△ Breakout Watch</div>
        <div style='font-family:IBM Plex Mono,monospace; font-size:0.62rem;
                    color:{RH_MUTED}; margin-top:6px; letter-spacing:0.18em;
                    text-transform:uppercase;'>Nifty 500 · Daily · CMT</div>
    </div>""", unsafe_allow_html=True)

    threshold_atr = st.slider("Gap to SH (ATRs)", 0.3, 3.0, 1.5, 0.1)
    lookback      = st.slider("Swing lookback", 5, 15, 10)
    min_mcap      = st.slider("Min market cap (₹ Cr)", 500, 10000, 500, 250)
    days_back     = st.slider("Breakout window (days)", 1, 10, 5, 1)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)
    run_btn = st.button("RUN SCREEN", use_container_width=True, type="primary")

    st.markdown(f"""
    <div style='margin-top:22px; padding:12px; background:{RH_BG};
                border:1px solid {RH_BORDER};'>
        <div style='font-family:IBM Plex Mono,monospace; font-size:0.58rem;
                    color:{RH_GOLD_LIGHT}; text-transform:uppercase;
                    letter-spacing:0.16em; margin-bottom:10px; font-weight:500;'>
            Active Filters · CMT
        </div>
        <div style='font-family:IBM Plex Mono,monospace; font-size:0.7rem;
                    color:{RH_TEXT}; line-height:1.9; letter-spacing:0.04em;'>
            ① Nifty regime check<br>
            ② Relative Strength &gt; Nifty<br>
            ③ ATR-normalized distance<br>
            ④ Tight base (SD ≤ 4%)<br>
            ⑤ Wyckoff volume absorption<br>
            ⑥ Level integrity<br>
            ⑦ Chop zone rejection<br>
            ⑧ 2-candle confirmation
        </div>
    </div>""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  SESSION STATE
# ═══════════════════════════════════════════════════════════════
if "sw_results"   not in st.session_state: st.session_state.sw_results = None
if "sw_breakouts" not in st.session_state: st.session_state.sw_breakouts = None
if "sw_risk_on"   not in st.session_state: st.session_state.sw_risk_on = True

if run_btn:
    with st.spinner("Downloading Nifty 500 data in batch · scanning signals · ~60–90 sec…"):
        st.session_state.sw_results,   st.session_state.sw_risk_on = run_approaching(
            lookback, min_mcap, threshold_atr
        )
        st.session_state.sw_breakouts, _ = run_breakouts(lookback, min_mcap, days_back)


if st.session_state.sw_results is None:
    st.markdown(f"""
    <div class="empty-state">
        <div class="empty-state-orn">△</div>
        <div class="empty-state-text">Awaiting your instructions</div>
        <div class="empty-state-sub">Configure filters and press Run Screen</div>
        <div style='margin-top:36px; padding:16px 24px; display:inline-block;
                    background:{RH_SURFACE}; border:1px solid {RH_GOLD_DIM};
                    font-family:IBM Plex Mono,monospace; font-size:0.78rem;
                    color:{RH_GOLD_LIGHT}; letter-spacing:0.08em;'>
            ◀ Open the sidebar from the top-left to access filters
        </div>
        <div style='margin-top:14px; font-family:IBM Plex Mono,monospace;
                    font-size:0.68rem; color:{RH_MUTED}; letter-spacing:0.06em;'>
            If the sidebar arrow isn't visible, look for "&gt;" at the very
            top-left edge of the page · or use the keyboard shortcut
            <kbd style='background:{RH_BG}; padding:2px 6px; border:1px solid {RH_BORDER};
                        color:{RH_GOLD_LIGHT};'>Ctrl/Cmd + Shift + .</kbd>
        </div>
    </div>""", unsafe_allow_html=True)
    if st.button("← BACK TO HUB", key="back_empty"):
        st.switch_page("Home.py")
    st.stop()


# Risk-off banner
if not st.session_state.sw_risk_on:
    st.markdown(f"""
    <div style='background:rgba(231,76,60,0.06); border:1px solid {RH_RED};
                border-left:4px solid {RH_RED}; padding:14px 20px;
                margin-bottom:18px;'>
        <div style='font-family:Fraunces,serif; font-weight:700; color:{RH_RED};
                    font-size:0.95rem;'>
            ⚠ Market Regime: RISK-OFF
        </div>
        <div style='font-family:IBM Plex Mono,monospace; font-size:0.72rem;
                    color:{RH_TEXT}; margin-top:6px; letter-spacing:0.04em;'>
            Nifty is below its 50-day MA. Breakouts fail more often in such phases.
            Consider waiting for regime confirmation.
        </div>
    </div>""", unsafe_allow_html=True)


tab1, tab2, tab3 = st.tabs(["APPROACHING", "RECENT BREAKOUTS", "VALIDATE LOGIC"])


# ─────────────────────────────────────────────────────
#  CHART RENDERER (shared between tabs 1 and 2)
# ─────────────────────────────────────────────────────
def render_chart(sel):
    try:
        import yfinance as yf
        df_c = yf.Ticker(sel["full_sym"]).history(period="1y", interval="1d")
        fig = make_subplots(
            rows=2, cols=1, shared_xaxes=True,
            row_heights=[0.72, 0.28], vertical_spacing=0.03
        )
        fig.add_trace(go.Candlestick(
            x=df_c.index, open=df_c['Open'], high=df_c['High'],
            low=df_c['Low'], close=df_c['Close'],
            increasing_line_color=RH_GREEN, decreasing_line_color=RH_RED,
            increasing_fillcolor=RH_GREEN, decreasing_fillcolor=RH_RED,
            name="Price", line_width=1
        ), row=1, col=1)

        sh_level = sel.get("swing_high") or sel.get("broken_sh")
        if sh_level:
            label = f"Resistance ₹{sh_level:,}"
            if sel.get("gap_pct") is not None:
                label += f"  ·  {sel.get('gap_pct')}% / {sel.get('gap_atr','?')} ATR"
            elif sel.get("bo_pct"):
                label += f"  ·  broke +{sel['bo_pct']}%"
            fig.add_hline(
                y=sh_level, line_dash="dash", line_color=RH_GOLD, line_width=1.5,
                annotation_text=label, annotation_position="top left",
                annotation_font=dict(color=RH_GOLD_LIGHT, size=10, family="IBM Plex Mono"),
                row=1, col=1
            )
        if sel.get("swing_low"):
            fig.add_hline(
                y=sel["swing_low"], line_dash="dot", line_color="#5DA9C7", line_width=1.2,
                annotation_text=f"Support ₹{sel['swing_low']:,}",
                annotation_position="bottom left",
                annotation_font=dict(color="#5DA9C7", size=10, family="IBM Plex Mono"),
                row=1, col=1
            )

        sh_d = [s[0] for s in sel["sh_list"]]
        sh_p = [s[1] for s in sel["sh_list"]]
        fig.add_trace(go.Scatter(
            x=sh_d, y=sh_p, mode='markers',
            marker=dict(color=RH_GOLD, size=8, symbol='triangle-down',
                        line=dict(color=RH_MAROON, width=1)),
            name="Swing Highs"
        ), row=1, col=1)

        sl_d = [s[0] for s in sel["sl_list"]]
        sl_p = [s[1] for s in sel["sl_list"]]
        fig.add_trace(go.Scatter(
            x=sl_d, y=sl_p, mode='markers',
            marker=dict(color="#5DA9C7", size=8, symbol='triangle-up',
                        line=dict(color="#3A7A95", width=1)),
            name="Swing Lows"
        ), row=1, col=1)

        vol_c = ['rgba(46,204,113,0.5)' if c >= o else 'rgba(231,76,60,0.5)'
                 for c, o in zip(df_c['Close'], df_c['Open'])]
        fig.add_trace(go.Bar(x=df_c.index, y=df_c['Volume'],
                              marker_color=vol_c, showlegend=False), row=2, col=1)

        avg_v = df_c['Volume'].rolling(20).mean()
        fig.add_trace(go.Scatter(
            x=df_c.index, y=avg_v,
            line=dict(color='rgba(212,168,48,0.6)', width=1, dash='dot'),
            showlegend=False
        ), row=2, col=1)

        fig.update_layout(
            height=500, plot_bgcolor="#F5ECD7", paper_bgcolor="#EDE2C8",
            font=dict(family='IBM Plex Mono', color=RH_MUTED, size=10),
            xaxis_rangeslider_visible=False,
            margin=dict(l=10, r=10, t=10, b=10),
            legend=dict(orientation='h', y=1.04, x=0,
                         font=dict(size=9, color=RH_MUTED),
                         bgcolor='rgba(0,0,0,0)'),
            hoverlabel=dict(bgcolor="#FFFFFF", bordercolor=RH_MAROON,
                             font=dict(family='IBM Plex Mono', color=RH_TEXT))
        )
        fig.update_xaxes(gridcolor='rgba(139,26,26,0.1)', zeroline=False,
                          linecolor="rgba(139,26,26,0.2)")
        fig.update_yaxes(gridcolor='rgba(139,26,26,0.1)', zeroline=False,
                          linecolor="rgba(139,26,26,0.2)")
        st.plotly_chart(fig, use_container_width=True,
                         config={"displayModeBar": False})
    except Exception as e:
        st.error(f"Chart error: {e}")


# ═══════════════════════════════════════════════════════════════
#  TAB 1 — APPROACHING
# ═══════════════════════════════════════════════════════════════
with tab1:
    results = st.session_state.sw_results
    total = len(results)
    hot   = sum(1 for r in results if r["tier"] == "HOT")
    warm  = sum(1 for r in results if r["tier"] == "WARM")
    wy    = sum(1 for r in results if r["wyckoff_ok"])
    avg_rs = round(sum(r["rs_diff"] for r in results) / total, 1) if total else 0

    st.markdown(f"""
    <div class="kpi-row">
        <div class="kpi"><div class="kpi-val" style="color:{RH_GOLD_LIGHT}">{total}</div>
            <div class="kpi-lbl">Setups</div></div>
        <div class="kpi"><div class="kpi-val" style="color:{RH_RED}">{hot}</div>
            <div class="kpi-lbl">Hot ≤ 0.5 ATR</div></div>
        <div class="kpi"><div class="kpi-val" style="color:{RH_GOLD_LIGHT}">{warm}</div>
            <div class="kpi-lbl">Warm ≤ 1.0 ATR</div></div>
        <div class="kpi"><div class="kpi-val" style="color:{RH_GREEN}">{wy}</div>
            <div class="kpi-lbl">Wyckoff Accumulation</div></div>
        <div class="kpi"><div class="kpi-val" style="color:#5DA9C7">+{avg_rs}%</div>
            <div class="kpi-lbl">Avg RS vs Nifty</div></div>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div class="section-head">
        <span class="section-head-label">Dispatch 01</span>
        Stocks Approaching Resistance
    </div>""", unsafe_allow_html=True)

    if not results:
        st.markdown("""<div class="empty-state">
            <div class="empty-state-orn">∅</div>
            <div class="empty-state-text">No approaching setups</div>
            <div class="empty-state-sub">All 8 CMT filters applied — market may be thin today</div>
        </div>""", unsafe_allow_html=True)
    else:
        rows_html = ""
        for r in results:
            sc = SECTOR_COLORS.get(r["sector"], RH_MUTED)
            dc = RH_GREEN if r["day_chg"] >= 0 else RH_RED
            pcls = {"HOT": "pill-hot", "WARM": "pill-warm", "CLOSE": "pill-cool"}[r["tier"]]
            plbl = {"HOT": "◆ HOT", "WARM": "◇ WARM", "CLOSE": "◌ CLOSE"}[r["tier"]]
            prox_pct = max(0, min(100, round((1 - r["gap_atr"] / max(threshold_atr, 0.1)) * 100)))
            pcol = RH_RED if r["tier"] == "HOT" else RH_GOLD_LIGHT if r["tier"] == "WARM" else "#8E6FD8"
            wy_badge = "◉" if r["wyckoff_ok"] else "◎"
            wy_col   = RH_GREEN if r["wyckoff_ok"] else RH_MUTED
            rs_col   = RH_GREEN if r["rs_diff"] > 5 else RH_GOLD_LIGHT if r["rs_diff"] > 0 else RH_MUTED

            rows_html += f"""
            <div class="tbl-row">
                <span class="sym">{r['symbol']}</span>
                <span><span class="pill {pcls}">{plbl}</span></span>
                <span class="mono">₹{r['close']:,}<br>
                    <span style="font-size:0.68rem; color:{dc}; font-weight:500;">
                        {'+' if r['day_chg']>=0 else ''}{r['day_chg']}%</span>
                </span>
                <span class="mono">₹{r['swing_high']:,}<br>
                    <span style="font-size:0.62rem; color:{RH_MUTED};">{r['sh_date']}</span>
                </span>
                <span>
                    <div class="prox">
                        <div class="prox-bg">
                            <div class="prox-fill"
                                 style="width:{prox_pct}%; background:{pcol};
                                        box-shadow:0 0 6px {pcol}60;"></div>
                        </div>
                        <span style="font-family:IBM Plex Mono; font-size:0.7rem;
                                     color:{pcol}; min-width:48px; font-weight:500;">
                            {r['gap_atr']}σ
                        </span>
                    </div>
                    <div style="font-size:0.58rem; color:{RH_MUTED};
                                font-family:IBM Plex Mono; margin-top:3px;">
                        {r['gap_pct']}% · pb {r['pullback']}% · base σ{r['base_sd']}%
                    </div>
                </span>
                <span style="font-family:IBM Plex Mono; font-size:0.74rem; color:{wy_col};">
                    {wy_badge} {r['vol_ratio']}×
                    <div style="font-size:0.58rem; color:{RH_MUTED}; margin-top:2px;">
                        U/D {r['wyckoff_ratio']}
                    </div>
                </span>
                <span style="font-family:IBM Plex Mono; font-size:0.7rem;
                             color:{rs_col}; font-weight:500;">
                    {'+' if r['rs_diff']>=0 else ''}{r['rs_diff']}%
                    <div style="font-size:0.56rem; color:{RH_MUTED}; font-weight:400;
                                text-transform:uppercase; letter-spacing:0.1em;">
                        RS · ADX {r['adx']}
                    </div>
                </span>
                <span>
                    <span class="sec" style="background:{sc}18; color:{sc};
                                              border:1px solid {sc}50;">
                        {r['sector']}
                    </span>
                    <div style="font-family:IBM Plex Mono; font-size:0.58rem;
                                color:{RH_MUTED}; margin-top:4px;">
                        ₹{r['mcap_cr']:,}Cr
                    </div>
                </span>
            </div>"""

        st.markdown(f"""
        <div class="tbl">
          <div class="tbl-hdr">
            <span>Symbol</span><span>Tier</span><span>Close</span>
            <span>Resistance</span><span>Distance</span>
            <span>Vol / Wyckoff</span><span>RS / ADX</span><span>Sector</span>
          </div>
          <div class="scroll-body">{rows_html}</div>
        </div>""", unsafe_allow_html=True)

        st.markdown("""<div class="section-head">
            <span class="section-head-label">Visual</span>
            Chart Detail
        </div>""", unsafe_allow_html=True)
        sel_sym = st.selectbox(
            "Select stock", [r["symbol"] for r in results],
            key="sel_t1", label_visibility="collapsed"
        )
        if sel_sym:
            s = next(r for r in results if r["symbol"] == sel_sym)
            render_chart(s)
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Close",      f"₹{s['close']:,}",       f"{s['day_chg']}%")
            c2.metric("Resistance", f"₹{s['swing_high']:,}",  f"{s['gap_atr']}σ")
            c3.metric("Pullback",   f"{s['pullback']}%",      f"base σ{s['base_sd']}%")
            c4.metric("RS (3M)",    f"+{s['rs_diff']}%",      f"ADX {s['adx']}")
            c5.metric(
                "Wyckoff",
                "Accumulation" if s['wyckoff_ok'] else "Weak",
                f"U/D {s['wyckoff_ratio']}"
            )


# ═══════════════════════════════════════════════════════════════
#  TAB 2 — RECENT BREAKOUTS
# ═══════════════════════════════════════════════════════════════
with tab2:
    bos = st.session_state.sw_breakouts or []
    total_b = len(bos)
    today_b = sum(1 for b in bos if b["days_ago"] == 1)
    conf_b  = sum(1 for b in bos if b["confirmation"] in ("2-candle", "volume"))
    avg_bo  = round(sum(b["bo_pct"] for b in bos) / total_b, 2) if total_b else 0

    st.markdown(f"""
    <div class="kpi-row">
        <div class="kpi"><div class="kpi-val" style="color:{RH_GOLD_LIGHT}">{total_b}</div>
            <div class="kpi-lbl">Breakouts</div></div>
        <div class="kpi"><div class="kpi-val" style="color:{RH_RED}">{today_b}</div>
            <div class="kpi-lbl">Today</div></div>
        <div class="kpi"><div class="kpi-val" style="color:{RH_GOLD_LIGHT}">{total_b - today_b}</div>
            <div class="kpi-lbl">Last {days_back}d</div></div>
        <div class="kpi"><div class="kpi-val" style="color:{RH_GREEN}">{conf_b}</div>
            <div class="kpi-lbl">Confirmed</div></div>
        <div class="kpi"><div class="kpi-val" style="color:#5DA9C7">+{avg_bo}%</div>
            <div class="kpi-lbl">Avg Breakout</div></div>
    </div>""", unsafe_allow_html=True)

    st.markdown("""<div class="section-head">
        <span class="section-head-label">Dispatch 02</span>
        Confirmed Breakouts
    </div>""", unsafe_allow_html=True)

    if not bos:
        st.markdown("""<div class="empty-state">
            <div class="empty-state-orn">∅</div>
            <div class="empty-state-text">No confirmed breakouts</div>
            <div class="empty-state-sub">Requires 2-candle hold or 1.5× volume</div>
        </div>""", unsafe_allow_html=True)
    else:
        bo_html = ""
        for b in bos:
            sc = SECTOR_COLORS.get(b["sector"], RH_MUTED)
            dc = RH_GREEN if b["day_chg"] >= 0 else RH_RED
            day_pill = "pill-hot" if b["days_ago"] == 1 else "pill-warm"
            conf = b["confirmation"]
            conf_badge = ("◉ 2-candle" if conf == "2-candle"
                          else "◉ volume" if conf == "volume"
                          else "◎ pending")
            conf_col = RH_GREEN if conf != "pending" else RH_GOLD_LIGHT
            rs_col = RH_GREEN if b["rs_diff"] > 5 else RH_GOLD_LIGHT if b["rs_diff"] > 0 else RH_MUTED

            bo_html += f"""
            <div class="tbl-row">
                <span class="sym">{b['symbol']}</span>
                <span><span class="pill {day_pill}">{b['label']}</span></span>
                <span class="mono">₹{b['close']:,}<br>
                    <span style="font-size:0.68rem; color:{dc}; font-weight:500;">
                        {'+' if b['day_chg']>=0 else ''}{b['day_chg']}%</span>
                </span>
                <span class="mono">₹{b['broken_sh']:,}<br>
                    <span style="font-size:0.58rem; color:{RH_MUTED};">set {b['sh_date']}</span>
                </span>
                <span style="font-family:Fraunces,serif; font-size:1rem;
                             color:{RH_GREEN}; font-weight:700;">
                    +{b['bo_pct']}%
                    <div style="font-family:IBM Plex Mono; font-size:0.6rem;
                                color:{conf_col}; font-weight:500; margin-top:2px;">
                        {conf_badge}
                    </div>
                </span>
                <span style="font-family:IBM Plex Mono; font-size:0.74rem; color:{RH_TEXT};">
                    {b['vol_ratio']}×
                    <div style="font-size:0.56rem; color:{RH_MUTED}; margin-top:2px;">
                        ADX {b['adx']}
                    </div>
                </span>
                <span style="font-family:IBM Plex Mono; font-size:0.7rem;
                             color:{rs_col}; font-weight:500;">
                    +{b['rs_diff']}%
                    <div style="font-size:0.56rem; color:{RH_MUTED}; font-weight:400;
                                text-transform:uppercase; letter-spacing:0.1em;">RS</div>
                </span>
                <span>
                    <span class="sec" style="background:{sc}18; color:{sc};
                                              border:1px solid {sc}50;">
                        {b['sector']}
                    </span>
                    <div style="font-family:IBM Plex Mono; font-size:0.58rem;
                                color:{RH_MUTED}; margin-top:4px;">
                        ₹{b['mcap_cr']:,}Cr
                    </div>
                </span>
            </div>"""

        st.markdown(f"""
        <div class="tbl">
          <div class="tbl-hdr">
            <span>Symbol</span><span>When</span><span>Close</span>
            <span>Broken Level</span><span>Breakout</span>
            <span>Volume</span><span>RS</span><span>Sector</span>
          </div>
          <div class="scroll-body">{bo_html}</div>
        </div>""", unsafe_allow_html=True)

        st.markdown("""<div class="section-head">
            <span class="section-head-label">Visual</span>
            Chart Detail
        </div>""", unsafe_allow_html=True)
        sel2 = st.selectbox(
            "Select stock", [b["symbol"] for b in bos],
            key="sel_t2", label_visibility="collapsed"
        )
        if sel2:
            b = next(x for x in bos if x["symbol"] == sel2)
            render_chart(b)
            c1, c2, c3, c4, c5 = st.columns(5)
            c1.metric("Close",    f"₹{b['close']:,}",     f"{b['day_chg']}%")
            c2.metric("Broke",    f"₹{b['broken_sh']:,}", b['label'])
            c3.metric("Breakout", f"+{b['bo_pct']}%",     b["confirmation"])
            c4.metric("Volume",   f"{b['vol_ratio']}×",   f"ADX {b['adx']}")
            c5.metric("RS (3M)",  f"+{b['rs_diff']}%")


# ═══════════════════════════════════════════════════════════════
#  TAB 3 — VALIDATE LOGIC (BACKTEST)
# ═══════════════════════════════════════════════════════════════
with tab3:
    st.markdown(f"""
    <div style='background:{RH_SURFACE}; border:1px solid {RH_BORDER};
                border-left:3px solid {RH_GOLD_DIM}; padding:16px 20px;
                margin-bottom:22px;'>
        <div style='font-family:Fraunces,serif; font-size:1rem; font-weight:700;
                    color:{RH_GOLD_LIGHT}; margin-bottom:8px;'>
            Validating the Screener's Historical Accuracy
        </div>
        <div style='font-family:IBM Plex Mono,monospace; font-size:0.78rem;
                    color:{RH_TEXT}; line-height:1.7; letter-spacing:0.04em;'>
            Select any stock. The engine walks through 2 years of history, flags every
            breakout the screener would have caught, and marks each as
            <span style='color:{RH_GREEN};'>Real</span>,
            <span style='color:{RH_GOLD_LIGHT};'>Weak</span>, or
            <span style='color:{RH_RED};'>False</span>.
        </div>
    </div>""", unsafe_allow_html=True)

    all_symbols = sorted([s.replace(".NS", "") for s in WATCHLIST])
    bt_symbol = st.selectbox(
        "Stock to validate", all_symbols, key="bt_sym",
        index=all_symbols.index("TITAN") if "TITAN" in all_symbols else 0
    )
    bt_run = st.button("VALIDATE", key="bt_btn", use_container_width=True)

    if bt_run:
        with st.spinner(f"Walking through 2 years of {bt_symbol}..."):
            try:
                import yfinance as yf
                df = yf.Ticker(f"{bt_symbol}.NS").history(period="2y", interval="1d")
                if df.empty:
                    st.error("No data available.")
                    st.stop()
                signals = []
                checked = set()
                closes  = df['Close'].values
                min_bars = lookback * 2 + 30
                for i in range(min_bars, len(df)):
                    df_s = df.iloc[:i]
                    sh_s, _ = find_swings(df_s, lookback)
                    close_now  = float(df_s['Close'].iloc[-1])
                    prev_close = float(df_s['Close'].iloc[-2])
                    if i >= 50:
                        ma50 = float(df_s['Close'].iloc[-50:].mean())
                        if close_now < ma50 * 0.97:
                            continue
                    val = find_valid_resistance(df_s, sh_s, threshold_atr_mult=10.0)
                    if not val:
                        continue
                    sh_price = val["price"]
                    key = round(sh_price, 1)
                    if key in checked:
                        continue
                    if prev_close <= sh_price < close_now:
                        checked.add(key)
                        future = closes[i: i + 10]
                        if len(future) > 0:
                            max_gain = round((future.max() - sh_price) / sh_price * 100, 2)
                            min_draw = round((future.min() - sh_price) / sh_price * 100, 2)
                            if max_gain >= 3:
                                result, tag = f"Real breakout (+{max_gain}% in 10d)", "real"
                            elif max_gain >= 1:
                                result, tag = f"Weak follow-through (peak +{max_gain}%)", "weak"
                            else:
                                result, tag = f"False breakout ({min_draw}% to +{max_gain}%)", "false"
                        else:
                            result, tag = "Too recent", "recent"
                        signals.append({
                            "Date": df_s.index[-1].strftime("%d %b '%y"),
                            "Broke Above": f"₹{sh_price:,}",
                            "Set On": val["date"].strftime("%d %b '%y"),
                            "Pullback": f"{val['pullback_pct']}%",
                            "Gap (ATR)": f"{val['gap_atr']}σ",
                            "Base SD": f"{val['base_sd_pct']}%",
                            "Outcome": result, "_tag": tag,
                        })

                total = len(signals)
                real  = sum(1 for s in signals if s["_tag"] == "real")
                weak  = sum(1 for s in signals if s["_tag"] == "weak")
                false = sum(1 for s in signals if s["_tag"] == "false")
                acc   = round(real / total * 100, 1) if total else 0

                if acc >= 70:
                    verdict, vc = "LOGIC IS SOLID", RH_GREEN
                elif acc >= 50:
                    verdict, vc = "LOGIC IS DECENT", RH_GOLD_LIGHT
                elif total == 0:
                    verdict, vc = "NO BREAKOUTS IN 2Y", RH_MUTED
                else:
                    verdict, vc = "LOGIC NEEDS WORK", RH_RED

                st.markdown("""<div class="section-head">
                    <span class="section-head-label">Report</span>
                    Signal Accuracy
                </div>""", unsafe_allow_html=True)

                st.markdown(f"""
                <div class="kpi-row">
                    <div class="kpi"><div class="kpi-val" style="color:{RH_GOLD_LIGHT}">{total}</div>
                        <div class="kpi-lbl">Detected</div></div>
                    <div class="kpi"><div class="kpi-val" style="color:{RH_GREEN}">{real}</div>
                        <div class="kpi-lbl">Real</div></div>
                    <div class="kpi"><div class="kpi-val" style="color:{RH_GOLD_LIGHT}">{weak}</div>
                        <div class="kpi-lbl">Weak</div></div>
                    <div class="kpi"><div class="kpi-val" style="color:{RH_RED}">{false}</div>
                        <div class="kpi-lbl">False</div></div>
                    <div class="kpi"><div class="kpi-val" style="color:{vc}">{acc}%</div>
                        <div class="kpi-lbl">{verdict}</div></div>
                </div>""", unsafe_allow_html=True)

                if signals:
                    st.markdown("""<div class="section-head">
                        <span class="section-head-label">Detail</span>
                        Every Historical Breakout
                    </div>""", unsafe_allow_html=True)
                    for s in signals:
                        s.pop("_tag", None)
                    df_sig = pd.DataFrame(signals)
                    st.dataframe(
                        df_sig, use_container_width=True, hide_index=True,
                        height=min(500, 42 * len(signals) + 45)
                    )

                    st.markdown("""<div class="section-head">
                        <span class="section-head-label">Visual</span>
                        Breakouts Plotted on Chart
                    </div>""", unsafe_allow_html=True)
                    fig = make_subplots(rows=1, cols=1)
                    fig.add_trace(go.Candlestick(
                        x=df.index, open=df['Open'], high=df['High'],
                        low=df['Low'], close=df['Close'],
                        increasing_line_color=RH_GREEN, decreasing_line_color=RH_RED,
                        increasing_fillcolor=RH_GREEN, decreasing_fillcolor=RH_RED,
                        name="Price", line_width=1
                    ))
                    bo_dates, bo_prices, bo_colors = [], [], []
                    for s in signals:
                        try:
                            dt = datetime.strptime(s["Date"], "%d %b '%y")
                            bo_dates.append(dt)
                            bo_prices.append(float(s["Broke Above"].replace("₹", "").replace(",", "")))
                            if "Real" in s["Outcome"]:    bo_colors.append(RH_GREEN)
                            elif "Weak" in s["Outcome"]:  bo_colors.append(RH_GOLD_LIGHT)
                            else:                          bo_colors.append(RH_RED)
                        except Exception:
                            continue
                    if bo_dates:
                        fig.add_trace(go.Scatter(
                            x=bo_dates, y=bo_prices, mode='markers',
                            marker=dict(symbol='diamond', size=14, color=bo_colors,
                                         line=dict(color=RH_BG, width=1)),
                            name="Signals"
                        ))
                    fig.update_layout(
                        height=480, plot_bgcolor="#F5ECD7", paper_bgcolor="#EDE2C8",
                        font=dict(family='IBM Plex Mono', color=RH_MUTED, size=10),
                        xaxis_rangeslider_visible=False, showlegend=False,
                        margin=dict(l=10, r=10, t=10, b=10)
                    )
                    fig.update_xaxes(gridcolor='rgba(139,26,26,0.1)', zeroline=False,
                                      linecolor="rgba(139,26,26,0.2)")
                    fig.update_yaxes(gridcolor='rgba(139,26,26,0.1)', zeroline=False,
                                      linecolor="rgba(139,26,26,0.2)")
                    st.plotly_chart(fig, use_container_width=True,
                                     config={"displayModeBar": False})

                    st.markdown(f"""
                    <div style='font-family:IBM Plex Mono,monospace; font-size:0.65rem;
                                color:{RH_MUTED}; margin-top:8px; line-height:2;
                                letter-spacing:0.06em;'>
                        ◆ <span style='color:{RH_GREEN};'>GREEN</span> — real (≥3% in 10d)  ·
                        ◆ <span style='color:{RH_GOLD_LIGHT};'>GOLD</span> — weak follow-through  ·
                        ◆ <span style='color:{RH_RED};'>RED</span> — false breakout
                    </div>""", unsafe_allow_html=True)
                else:
                    st.info("No breakouts detected — the stock had no clean setups in 2 years.")
            except Exception as e:
                st.error(f"Validation failed: {e}")


st.markdown("<br>", unsafe_allow_html=True)
if st.button("← BACK TO HUB", key="back_bottom", use_container_width=True):
    st.switch_page("Home.py")
