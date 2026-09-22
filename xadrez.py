from pathlib import Path
import re

path = Path("/mnt/data/xadrez_2d.html")
html = path.read_text(encoding="utf-8")

# Replace board colors and enhance pieces
html = html.replace('--light: #f0d9b5;\n    --dark: #b58863;', '--light: #dbe5f0;\n    --dark: #6682a3;')
html = html.replace(
'''  .piece {
    position: relative;
    z-index: 2;
    transform: translateY(-1px);
    text-shadow: 0 2px 2px rgba(0,0,0,.28);
  }
  .white-piece { color: #fff; text-shadow: 0 2px 0 #333, 0 0 3px #111; }
  .black-piece { color: #111; text-shadow: 0 1px 1px rgba(255,255,255,.18); }''',
'''  .piece {
    position: relative;
    z-index: 2;
    transform: translateY(-2px);
    font-family: "DejaVu Sans", "Segoe UI Symbol", "Noto Sans Symbols 2", serif;
    font-weight: 700;
    filter: drop-shadow(0 3px 2px rgba(0,0,0,.28));
    transition: transform .12s ease, filter .12s ease;
  }
  .square:hover .piece {
    transform: translateY(-4px) scale(1.04);
    filter: drop-shadow(0 5px 3px rgba(0,0,0,.30));
  }
  .white-piece {
    color: #f8fbff;
    -webkit-text-stroke: 1.4px #2f3945;
    text-shadow: 0 1px 0 #fff, 0 3px 5px rgba(0,0,0,.35);
  }
  .black-piece {
    color: #202833;
    -webkit-text-stroke: .7px #0d1117;
    text-shadow: 0 1px 0 rgba(255,255,255,.26), 0 3px 4px rgba(0,0,0,.25);
  }'''
)

# Add styles for select/settings
insert_css = r'''
  .settings {
    display: grid;
    gap: 10px;
    margin: 14px 0;
  }
  .field {
    display: grid;
    gap: 6px;
  }
  .field label {
    font-size: .8rem;
    color: #bdc8d3;
    font-weight: 700;
  }
  select {
    width: 100%;
    background: #15191d;
    color: #f4f4f4;
    border: 1px solid #46515d;
    border-radius: 7px;
    padding: 9px 10px;
    outline: none;
  }
  select:focus { border-color: #6fa4ff; }
  .thinking {
    color: #9fc0ff;
    font-weight: 700;
    margin-top: 8px;
    min-height: 20px;
    font-size: .86rem;
  }
'''
html = html.replace('  .legend { margin-top: 12px; font-size: .82rem; color: #b8c0c8; line-height: 1.45; }',
                    '  .legend { margin-top: 12px; font-size: .82rem; color: #b8c0c8; line-height: 1.45; }\n' + insert_css)

# Replace panel HTML section
old_panel = '''    <div id="status" class="status">Brancas jogam.</div>
    <button class="control" id="newGame">Nova partida</button>
    <button class="control secondary" id="flip">Virar tabuleiro</button>
    <div class="moves" id="moves"><div>Nenhum movimento.</div></div>'''

new_panel = '''    <div id="status" class="status">Brancas jogam.</div>

    <div class="settings">
      <div class="field">
        <label for="gameMode">Modo de jogo</label>
        <select id="gameMode">
          <option value="pvp">Jogador vs Jogador</option>
          <option value="ai">Jogador vs IA</option>
        </select>
      </div>

      <div class="field" id="difficultyField" style="display:none">
        <label for="difficulty">Dificuldade da IA</label>
        <select id="difficulty">
          <option value="easy">Fácil</option>
          <option value="medium" selected>Médio</option>
          <option value="hard">Difícil</option>
        </select>
      </div>
    </div>

    <button class="control" id="newGame">Nova partida</button>
    <button class="control secondary" id="flip">Virar tabuleiro</button>
    <div id="thinking" class="thinking"></div>
    <div class="moves" id="moves"><div>Nenhum movimento.</div></div>'''

html = html.replace(old_panel, new_panel)

# Update legend
html = html.replace(
'''      Regras clássicas incluídas: movimentos legais, captura, xeque,
      xeque-mate, afogamento, roque, en passant, promoção e empate por
      material insuficiente/repetição/regra dos 50 movimentos.''',
'''      Regras clássicas incluídas: movimentos legais, captura, xeque,
      xeque-mate, afogamento, roque, en passant, promoção e empate por
      material insuficiente/repetição/regra dos 50 movimentos. No modo contra IA,
      você joga de brancas.'''
)

# Extend global JS variables
html = html.replace(
'let state, selected = null, legalForSelected = [], flipped = false, pendingPromotion = null;',
'''let state, selected = null, legalForSelected = [], flipped = false, pendingPromotion = null;
let gameMode = "pvp";
let aiDifficulty = "medium";
let aiThinking = false;'''
)

# Prevent input during AI turn
html = html.replace(
'''function chooseSquare(r,c) {
  if(state.gameOver) return;''',
'''function chooseSquare(r,c) {
  if(state.gameOver || aiThinking) return;
  if(gameMode==="ai" && state.turn==="b") return;'''
)

# Hook execute to trigger AI after render
html = html.replace(
'''  render();
}''',
'''  render();
  if(gameMode==="ai" && state.turn==="b" && !state.gameOver) {
    setTimeout(makeAIMove, 180);
  }
}''',
1)

# Add AI functions before showPromotion
ai_code = r'''
const pieceValues = { p:100, n:320, b:330, r:500, q:900, k:20000 };

function evaluateBoard(s) {
  let score=0;
  const centerBonus = [
    [0,0,0,0,0,0,0,0],
    [0,3,4,4,4,4,3,0],
    [0,4,8,10,10,8,4,0],
    [0,4,10,16,16,10,4,0],
    [0,4,10,16,16,10,4,0],
    [0,4,8,10,10,8,4,0],
    [0,3,4,4,4,4,3,0],
    [0,0,0,0,0,0,0,0]
  ];
  for(let r=0;r<8;r++) for(let c=0;c<8;c++) {
    const p=s.board[r][c];
    if(!p) continue;
    const sign=colorOf(p)==="b" ? 1 : -1;
    let val=pieceValues[typeOf(p)] || 0;
    if(typeOf(p)!=="k") val += centerBonus[r][c];
    if(typeOf(p)==="p") {
      val += (colorOf(p)==="b" ? r : 7-r) * 5;
    }
    score += sign*val;
  }

  // Small mobility bonus.
  const bMob=allLegalMoves({...s,turn:"b"},"b").length;
  const wMob=allLegalMoves({...s,turn:"w"},"w").length;
  score += (bMob-wMob)*2;

  if(inCheck(s.board,"w")) score += 22;
  if(inCheck(s.board,"b")) score -= 22;
  return score;
}

function minimax(s, depth, alpha, beta, maximizing) {
  const legal=allLegalMoves(s,s.turn);
  if(depth===0 || legal.length===0 || s.halfmove>=100 || insufficientMaterial(s)) {
    if(legal.length===0) {
      if(inCheck(s.board,s.turn)) return s.turn==="b" ? -999999-depth : 999999+depth;
      return 0;
    }
    return evaluateBoard(s);
  }

  if(maximizing) {
    let best=-Infinity;
    for(const m of legal) {
      const promo=m.promotion ? "q" : null;
      const child=applyMove(s,m,promo);
      const score=minimax(child,depth-1,alpha,beta,false);
      if(score>best) best=score;
      if(score>alpha) alpha=score;
      if(beta<=alpha) break;
    }
    return best;
  } else {
    let best=Infinity;
    for(const m of legal) {
      const promo=m.promotion ? "q" : null;
      const child=applyMove(s,m,promo);
      const score=minimax(child,depth-1,alpha,beta,true);
      if(score<best) best=score;
      if(score<beta) beta=score;
      if(beta<=alpha) break;
    }
    return best;
  }
}

function pickAIMove() {
  const legal=allLegalMoves(state,"b");
  if(!legal.length) return null;

  if(aiDifficulty==="easy") {
    // Mostly random, but occasionally prefers captures.
    const captures=legal.filter(m=>state.board[m.to[0]][m.to[1]] || m.enPassant);
    if(captures.length && Math.random()<0.35)
      return captures[Math.floor(Math.random()*captures.length)];
    return legal[Math.floor(Math.random()*legal.length)];
  }

  const depth = aiDifficulty==="medium" ? 2 : 3;
  let bestScore=-Infinity;
  let bestMoves=[];

  // Move ordering improves alpha-beta efficiency.
  legal.sort((a,b)=>{
    const ca=state.board[a.to[0]][a.to[1]];
    const cb=state.board[b.to[0]][b.to[1]];
    return (cb ? pieceValues[typeOf(cb)] : 0) - (ca ? pieceValues[typeOf(ca)] : 0);
  });

  for(const m of legal) {
    const promo=m.promotion ? "q" : null;
    const child=applyMove(state,m,promo);
    const score=minimax(child,depth-1,-Infinity,Infinity,false);
    if(score>bestScore) {
      bestScore=score;
      bestMoves=[m];
    } else if(score===bestScore) {
      bestMoves.push(m);
    }
  }
  return bestMoves[Math.floor(Math.random()*bestMoves.length)];
}

function makeAIMove() {
  if(gameMode!=="ai" || state.turn!=="b" || state.gameOver || aiThinking) return;
  aiThinking=true;
  document.getElementById("thinking").textContent="IA pensando...";
  render();

  setTimeout(()=>{
    const move=pickAIMove();
    aiThinking=false;
    document.getElementById("thinking").textContent="";
    if(move) execute(move, move.promotion ? "q" : null);
    else render();
  }, 80);
}
'''
html = html.replace('function showPromotion() {', ai_code + '\nfunction showPromotion() {')

# Ensure render displays thinking after it writes status/moves
html = html.replace(
'''  const status=gameStatus();
  document.getElementById("status").textContent=status;''',
'''  const status=gameStatus();
  document.getElementById("status").textContent =
    aiThinking ? "IA pensando..." : status;'''
)

# Replace bottom event listeners to include mode/difficulty
old_bottom = '''document.getElementById("newGame").onclick=()=>{
  state=newState();
  selected=null; legalForSelected=[]; pendingPromotion=null;
  state.positionCounts.set(positionKey(state),1);
  render();
};
document.getElementById("flip").onclick=()=>{ flipped=!flipped; render(); };

state=newState();
state.positionCounts.set(positionKey(state),1);
render();'''

new_bottom = '''function resetGame() {
  state=newState();
  selected=null;
  legalForSelected=[];
  pendingPromotion=null;
  aiThinking=false;
  document.getElementById("thinking").textContent="";
  state.positionCounts.set(positionKey(state),1);
  render();
}

document.getElementById("newGame").onclick=resetGame;
document.getElementById("flip").onclick=()=>{ flipped=!flipped; render(); };

document.getElementById("gameMode").onchange=(e)=>{
  gameMode=e.target.value;
  document.getElementById("difficultyField").style.display =
    gameMode==="ai" ? "grid" : "none";
  resetGame();
};

document.getElementById("difficulty").onchange=(e)=>{
  aiDifficulty=e.target.value;
  if(gameMode==="ai") resetGame();
};

state=newState();
state.positionCounts.set(positionKey(state),1);
render();'''

html = html.replace(old_bottom, new_bottom)

path.write_text(html, encoding="utf-8")
print(f"Atualizado: {path}")
print(f"Tamanho: {path.stat().st_size/1024:.1f} KB")
