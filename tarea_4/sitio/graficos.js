/* Gráficos interactivos del sitio de la tarea 4.
   Sin librerías: cada gráfico es un SVG que se dibuja con JavaScript y se vuelve a dibujar si cambia el ancho.
   Los datos vienen de datos.js (window.DATOS), que genera scripts/construir_sitio.py desde las salidas del proyecto.
   Los colores son variables CSS (estilo.css), así el modo oscuro cambia sin redibujar; solo el mapa se redibuja. */
(function () {
  "use strict";
  var D = window.DATOS;
  var NS = "http://www.w3.org/2000/svg";
  var SOL = "S/" + String.fromCharCode(160);   // espacio que no se parte: «S/ 51,47» siempre en una línea
  var MESES = ["ene.", "feb.", "mar.", "abr.", "may.", "jun.", "jul.", "ago.", "set.", "oct.", "nov.", "dic."];

  // ── Utilidades ────────────────────────────────────────────────────────────────────────────────────
  // Número con coma decimal y espacio de miles, como en el informe: 1 040,8
  function num(v, dec) {
    if (v === null || v === undefined || isNaN(v)) return "—";
    dec = dec === undefined ? 1 : dec;
    var partes = Math.abs(v).toFixed(dec).split(".");
    var entero = partes[0].replace(/\B(?=(\d{3})+(?!\d))/g, " ");
    return (v < 0 ? "−" : "") + entero + (partes[1] ? "," + partes[1] : "");
  }
  function mes(p) { var a = p.split("-"); return MESES[+a[1] - 1] + " " + a[0]; }
  function css(nombre) { return getComputedStyle(document.documentElement).getPropertyValue(nombre).trim(); }
  function nodo(tag, attrs, padre) {
    var e = document.createElementNS(NS, tag);
    for (var k in attrs) e.setAttribute(k, attrs[k]);
    if (padre) padre.appendChild(e);
    return e;
  }
  function texto(padre, x, y, contenido, attrs) {
    var a = { x: x, y: y, "font-size": 12, style: "fill: var(--tenue)" };
    for (var k in attrs) a[k] = attrs[k];
    var t = nodo("text", a, padre);
    t.textContent = contenido;
    return t;
  }
  var lienzo = document.createElement("canvas").getContext("2d");
  function medir(t, px) {
    lienzo.font = px + "px " + getComputedStyle(document.body).fontFamily;
    return lienzo.measureText(t).width;
  }
  function escapar(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }

  // Barra horizontal con el extremo de datos redondeado (4 px) y la base recta, pegada al eje.
  function barra(x, y, w, h) {
    if (w <= 0) return "";
    var r = Math.min(4, h / 2, w);
    return "M" + x + "," + y + "h" + (w - r) + "a" + r + "," + r + " 0 0 1 " + r + "," + r + "v" + (h - 2 * r) +
      "a" + r + "," + r + " 0 0 1 " + (-r) + "," + r + "h" + (-(w - r)) + "z";
  }

  // Un solo cuadro flotante (tooltip) para toda la página.
  var aviso = document.createElement("div");
  aviso.className = "aviso-tooltip";
  aviso.setAttribute("role", "status");
  document.body.appendChild(aviso);
  function mostrar(html, ev) {
    aviso.innerHTML = html;
    aviso.classList.add("visible");
    var pad = 14, r = aviso.getBoundingClientRect();
    var x = ev.clientX + pad, y = ev.clientY + pad;
    if (x + r.width > innerWidth - 8) x = ev.clientX - r.width - pad;
    if (y + r.height > innerHeight - 8) y = ev.clientY - r.height - pad;
    aviso.style.left = Math.max(8, x) + "px";
    aviso.style.top = Math.max(8, y) + "px";
  }
  function ocultar() { aviso.classList.remove("visible"); }
  function filaAviso(color, nombre, valor) {
    return '<span class="fila"><i style="background: var(' + color + ')"></i>' + nombre + "<em>" + valor + "</em></span>";
  }

  // Redibuja cuando cambia el ancho del contenedor (no cuando cambia el alto, para no entrar en bucle).
  function alCambiarAncho(contenedor, dibujar) {
    var ancho = 0;
    new ResizeObserver(function () {
      var w = contenedor.clientWidth;
      // Se dibuja en el siguiente cuadro para no cambiar el tamaño dentro del propio aviso del observador.
      if (w && Math.abs(w - ancho) > 1) { ancho = w; requestAnimationFrame(function () { dibujar(w); }); }
    }).observe(contenedor);
    return function () { if (contenedor.clientWidth) dibujar(contenedor.clientWidth); };
  }

  function leyenda(id, series, tipo) {
    document.getElementById(id).innerHTML = series.map(function (s) {
      return '<span><i class="' + (tipo || "") + '" style="background: var(' + s.color + ')"></i>' + s.nombre + "</span>";
    }).join("");
  }

  function pestanas(id, opciones, alElegir) {
    var caja = document.getElementById(id);
    caja.innerHTML = opciones.map(function (o, i) {
      return '<button type="button" data-valor="' + o[0] + '" aria-pressed="' + (i === 0) + '">' + o[1] + "</button>";
    }).join("");
    caja.addEventListener("click", function (ev) {
      var b = ev.target.closest("button");
      if (!b) return;
      caja.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", x === b); });
      alElegir(b.dataset.valor);
    });
  }

  // ── Gráfico de líneas con guía vertical y tooltip ────────────────────────────────────────────────
  // cfg: { meses, series: [{nombre, corto, color, valores}], formato(v), extra(i) }
  function lineas(contenedor, cfg) {
    return alCambiarAncho(contenedor, function (W) {
      contenedor.innerHTML = "";
      var H = Math.round(Math.max(250, Math.min(380, W * 0.48)));
      var m = { t: 12, r: W < 520 ? 78 : 112, b: 28, l: 38 };
      var iw = W - m.l - m.r, ih = H - m.t - m.b, n = cfg.meses.length;
      var todos = [].concat.apply([], cfg.series.map(function (s) { return s.valores; }));
      var ymin = Math.min(100, Math.floor(Math.min.apply(null, todos) / 25) * 25);
      var ymax = Math.ceil(Math.max.apply(null, todos) / 25) * 25;
      var X = function (i) { return m.l + (i / (n - 1)) * iw; };
      var Y = function (v) { return m.t + ih - ((v - ymin) / (ymax - ymin)) * ih; };
      var svg = nodo("svg", { viewBox: "0 0 " + W + " " + H, height: H, role: "img", "aria-label": cfg.aria }, contenedor);

      var paso = ymax - ymin > 150 ? 50 : 25;
      for (var v = ymin; v <= ymax; v += paso) {
        nodo("line", { x1: m.l, x2: m.l + iw, y1: Y(v), y2: Y(v), style: "stroke: var(" + (v === 100 ? "--base" : "--rejilla") + ")" }, svg);
        texto(svg, m.l - 8, Y(v) + 4, num(v, 0), { "text-anchor": "end" });
      }
      var cada = W < 520 ? 5 : W < 820 ? 4 : 2;
      cfg.meses.forEach(function (p, i) {
        var a = p.split("-");
        if (a[1] === "01" && +a[0] % cada === 0) {
          nodo("line", { x1: X(i), x2: X(i), y1: m.t + ih, y2: m.t + ih + 4, style: "stroke: var(--base)" }, svg);
          texto(svg, X(i), m.t + ih + 18, a[0], { "text-anchor": "middle" });
        }
      });

      cfg.series.forEach(function (s) {
        var d = s.valores.map(function (v, i) { return (i ? "L" : "M") + X(i).toFixed(1) + "," + Y(v).toFixed(1); }).join("");
        nodo("path", { d: d, style: "fill: none; stroke: var(" + s.color + "); stroke-width: 2; stroke-linejoin: round" }, svg);
      });

      // Etiquetas directas al final de cada línea, separadas si quedan muy cerca.
      var fin = cfg.series.map(function (s) { return { s: s, y: Y(s.valores[n - 1]) }; }).sort(function (a, b) { return a.y - b.y; });
      for (var k = 1; k < fin.length; k++) if (fin[k].y - fin[k - 1].y < 32) fin[k].y = fin[k - 1].y + 32;
      fin.forEach(function (f) {
        nodo("circle", { cx: X(n - 1), cy: Y(f.s.valores[n - 1]), r: 4, style: "fill: var(" + f.s.color + "); stroke: var(--superficie); stroke-width: 2" }, svg);
        texto(svg, X(n - 1) + 10, f.y - 3, f.s.corto, { style: "fill: var(--tinta-2)" });
        texto(svg, X(n - 1) + 10, f.y + 13, cfg.formato(f.s.valores[n - 1]), { style: "fill: var(--tinta); font-weight: 600", "font-size": 13 });
      });

      var guia = nodo("line", { y1: m.t, y2: m.t + ih, visibility: "hidden", style: "stroke: var(--tenue); stroke-dasharray: 3 3" }, svg);
      var puntos = cfg.series.map(function (s) {
        return nodo("circle", { r: 4, visibility: "hidden", style: "fill: var(" + s.color + "); stroke: var(--superficie); stroke-width: 2" }, svg);
      });
      var zona = nodo("rect", { x: m.l, y: 0, width: iw + 6, height: m.t + ih, style: "fill: transparent; cursor: crosshair; touch-action: pan-y" }, svg);
      function mover(ev) {
        var r = svg.getBoundingClientRect();
        var x = (ev.clientX - r.left) * (W / r.width);
        var i = Math.max(0, Math.min(n - 1, Math.round(((x - m.l) / iw) * (n - 1))));
        guia.setAttribute("x1", X(i)); guia.setAttribute("x2", X(i)); guia.setAttribute("visibility", "visible");
        puntos.forEach(function (p, j) {
          p.setAttribute("cx", X(i)); p.setAttribute("cy", Y(cfg.series[j].valores[i])); p.setAttribute("visibility", "visible");
        });
        mostrar("<b>" + mes(cfg.meses[i]) + "</b>" + cfg.series.map(function (s) {
          return filaAviso(s.color, s.nombre, cfg.formato(s.valores[i]));
        }).join("") + (cfg.extra ? cfg.extra(i) : ""), ev);
      }
      zona.addEventListener("pointermove", mover);
      zona.addEventListener("pointerdown", mover);
      zona.addEventListener("pointerleave", function () {
        guia.setAttribute("visibility", "hidden");
        puntos.forEach(function (p) { p.setAttribute("visibility", "hidden"); });
        ocultar();
      });
    });
  }

  // ── Barras horizontales (una o dos series) ───────────────────────────────────────────────────────
  // cfg: { filas: [{id, etiqueta, valores}], series: [{nombre, color}], max, ref: {valor, etiqueta}, sufijo,
  //        aviso(fila) → html, alResaltar(id) }
  function barras(contenedor, cfg) {
    var grupos = {}, resaltado = null;
    function aplicar() {
      for (var id in grupos) grupos[id].style.opacity = resaltado === null || resaltado === id ? 1 : 0.35;
    }
    var redibujar = alCambiarAncho(contenedor, function (W) {
      contenedor.innerHTML = "";
      grupos = {};
      var ns = cfg.series.length, apilada = W < 460;
      var grosor = ns > 1 ? 11 : 14, hueco = 2, alto = ns * grosor + (ns - 1) * hueco;
      // Ancho de la columna de etiquetas: lo que mide la etiqueta más larga (si no cabe, pasan arriba de la barra).
      var masLarga = Math.max.apply(null, cfg.filas.map(function (f) { return medir(f.etiqueta, 13); }));
      if (masLarga + 14 > W * 0.45) apilada = true;
      var etiquetaW = apilada ? 0 : Math.ceil(masLarga) + 14;
      var filaH = apilada ? 20 + alto + 10 : Math.max(alto + 12, 24);
      var m = { t: cfg.ref ? 22 : 2, r: 50, b: 2, l: etiquetaW };
      var iw = W - m.l - m.r, H = m.t + cfg.filas.length * filaH + m.b;
      var todos = [].concat.apply([], cfg.filas.map(function (f) { return f.valores.filter(function (v) { return v !== null; }); }));
      var max = cfg.max || Math.max.apply(null, todos);
      var X = function (v) { return m.l + (v / max) * iw; };
      var svg = nodo("svg", { viewBox: "0 0 " + W + " " + H, height: H, role: "img", "aria-label": cfg.aria }, contenedor);

      cfg.filas.forEach(function (f, k) {
        var id = f.id || String(k);
        var g = nodo("g", {}, svg);
        grupos[id] = g;
        var y0 = m.t + k * filaH;
        var yb = apilada ? y0 + 20 : y0 + (filaH - alto) / 2;
        if (apilada) texto(g, m.l, y0 + 14, f.etiqueta, { style: "fill: var(--tinta)", "font-size": 13 });
        else texto(g, m.l - 10, yb + alto / 2 + 4, f.etiqueta, { "text-anchor": "end", style: "fill: var(--tinta)", "font-size": 13 });
        f.valores.forEach(function (v, s) {
          if (v === null) return;
          var y = yb + s * (grosor + hueco);
          nodo("path", { d: barra(m.l, y, X(v) - m.l, grosor), style: "fill: var(" + cfg.series[s].color + ")" }, g);
          texto(g, X(v) + 6, y + grosor / 2 + 4, num(v, 1) + (cfg.sufijo || ""), { class: "halo", style: "fill: var(--tinta-2)", "font-size": ns > 1 ? 11 : 12 });
        });
        var zona = nodo("rect", { x: 0, y: y0, width: W, height: filaH, style: "fill: transparent" }, g);
        function entrar(ev) {
          resaltado = id; aplicar();
          if (cfg.alResaltar) cfg.alResaltar(id);
          mostrar(cfg.aviso(f), ev);
        }
        zona.addEventListener("pointermove", entrar);
        zona.addEventListener("pointerdown", entrar);
        zona.addEventListener("pointerleave", function () {
          resaltado = null; aplicar();
          if (cfg.alResaltar) cfg.alResaltar(null);
          ocultar();
        });
      });
      nodo("line", { x1: m.l, x2: m.l, y1: m.t - 2, y2: H - m.b, style: "stroke: var(--base); pointer-events: none" }, svg);
      if (cfg.ref) {
        // La línea de referencia va detrás de las barras para no tapar las cifras.
        var x = X(cfg.ref.valor), cerca = x > W - 150;
        var linea = nodo("line", { x1: x, x2: x, y1: m.t - 4, y2: H - m.b, style: "stroke: var(--tinta-2); stroke-dasharray: 4 3; pointer-events: none" });
        svg.insertBefore(linea, svg.firstChild);
        texto(svg, cerca ? x - 4 : x + 4, m.t - 9, cfg.ref.etiqueta, { "text-anchor": cerca ? "end" : "start", style: "fill: var(--tinta-2)" });
      }
      aplicar();
    });
    return {
      redibujar: redibujar,
      resaltar: function (id) { resaltado = id; aplicar(); },
      cambiar: function (nuevo) { for (var k in nuevo) cfg[k] = nuevo[k]; redibujar(); },
    };
  }

  // ── Mapa coroplético ─────────────────────────────────────────────────────────────────────────────
  function colorEn(rampa, t) {
    t = Math.max(0, Math.min(1, t));
    var pos = t * (rampa.length - 1), i = Math.min(rampa.length - 2, Math.floor(pos)), f = pos - i;
    var a = rampa[i].match(/\w\w/g).map(function (h) { return parseInt(h, 16); });
    var b = rampa[i + 1].match(/\w\w/g).map(function (h) { return parseInt(h, 16); });
    return "rgb(" + a.map(function (x, j) { return Math.round(x + (b[j] - x) * f); }).join(",") + ")";
  }
  function mapa(contenedor, leyendaId, cfg) {
    var caminos = {}, resaltado = null;
    function aplicar() {
      for (var id in caminos) {
        var p = caminos[id], activo = id === resaltado;
        p.style.stroke = activo ? "var(--tinta)" : "var(--superficie)";
        p.style.strokeWidth = activo ? 2 : 0.8;
        if (activo) p.parentNode.appendChild(p);   // al frente, para que se vea el borde completo
      }
    }
    function dibujar() {
      contenedor.innerHTML = "";
      caminos = {};
      var M = cfg.mapa, rampa = css("--rampa").split(",").map(function (s) { return s.trim(); });
      var svg = nodo("svg", { viewBox: "-4 -4 " + (M.ancho + 8) + " " + (M.alto + 8), role: "img", "aria-label": cfg.aria }, contenedor);
      svg.style.maxHeight = "560px";
      Object.keys(M.trazos).forEach(function (id) {
        var p = nodo("path", { d: M.trazos[id], style: "fill: " + colorEn(rampa, cfg.valores[id] / cfg.vmax) + "; stroke: var(--superficie); stroke-width: 0.8; stroke-linejoin: round; cursor: pointer" }, svg);
        caminos[id] = p;
        function entrar(ev) { resaltado = id; aplicar(); cfg.alResaltar(id); mostrar(cfg.aviso(id), ev); }
        p.addEventListener("pointermove", entrar);
        p.addEventListener("pointerdown", entrar);
        p.addEventListener("pointerleave", function () { resaltado = null; aplicar(); cfg.alResaltar(null); ocultar(); });
      });
      // Leyenda continua de 0 a vmax con la marca del promedio nacional.
      var marcas = [];
      for (var v = 0; v <= cfg.vmax; v += 10) marcas.push('<span style="position:absolute;left:' + (v / cfg.vmax * 100) + '%;transform:translateX(-50%)">' + v + "</span>");
      document.getElementById(leyendaId).innerHTML =
        '<div style="max-width:300px;margin:6px auto 0;font-size:12px;color:var(--tenue)">' +
        '<div style="position:relative;height:16px;color:var(--tinta-2)"><span style="position:absolute;left:' + (cfg.ref / cfg.vmax * 100) + '%;transform:translateX(-50%);white-space:nowrap">▼ Perú ' + num(cfg.ref, 1) + " %</span></div>" +
        '<div style="height:10px;border-radius:3px;background:linear-gradient(90deg,' + rampa.join(",") + ')"></div>' +
        '<div style="position:relative;height:16px;margin-top:2px">' + marcas.join("") + "</div>" +
        '<div style="text-align:center;margin-top:2px">% de personas en pobreza</div></div>';
      aplicar();
    }
    dibujar();
    // El mapa usa colores calculados, así que se redibuja al cambiar de modo claro u oscuro.
    matchMedia("(prefers-color-scheme: dark)").addEventListener("change", dibujar);
    new MutationObserver(dibujar).observe(document.documentElement, { attributes: true, attributeFilter: ["data-theme"] });
    return { resaltar: function (id) { resaltado = id; aplicar(); } };
  }

  // ════════════════════════════════════════════════════════════════════════════════════════════════
  //  Hallazgo 1: IPC y calculadora
  // ════════════════════════════════════════════════════════════════════════════════════════════════
  var I = D.ipc, n = I.meses.length;
  var base100 = function (serie) { return serie.map(function (v) { return (v / serie[0]) * 100; }); };
  var seriesIpc = [
    { nombre: "IPC total", corto: "Total", color: "--s1", valores: base100(I.total) },
    { nombre: "Alimentos y bebidas", corto: "Alimentos", color: "--s2", valores: base100(I.alimentos) },
  ];
  leyenda("ley-ipc", seriesIpc, "linea");
  lineas(document.getElementById("g-ipc"), {
    meses: I.meses, series: seriesIpc, aria: "Gráfico de líneas del IPC total y de alimentos, diciembre de 2006 = 100",
    formato: function (v) { return num(v, 1); },
    extra: function (i) {
      return '<span class="fila" style="margin-top:4px;color:var(--tinta-2)">S/&nbsp;100 de este mes = S/&nbsp;' +
        num((100 * I.total[0]) / I.total[i], 2) + " de 2006</span>";
    },
  });

  var parteAlimentos = D.enaho.alimentos.pobres / 100;
  var canastas = {
    total: function (i) { return I.total[i] / I.total[0]; },
    alimentos: function (i) { return I.alimentos[i] / I.alimentos[0]; },
    pobres: function (i) {
      return parteAlimentos * (I.alimentos[i] / I.alimentos[0]) + (1 - parteAlimentos) * (I.sin_alimentos[i] / I.sin_alimentos[0]);
    },
  };
  var cMonto = document.getElementById("calc-monto"), cMes = document.getElementById("calc-mes"),
    cCanasta = document.getElementById("calc-canasta");
  cMes.max = n - 1;
  cMes.value = n - 1;
  function calcular() {
    var monto = Math.max(0, parseFloat(String(cMonto.value).replace(",", ".")) || 0);
    var i = +cMes.value, c = cCanasta.value, f = canastas[c](i);
    var valor = monto / f, perdida = (1 - 1 / f) * 100;
    document.getElementById("calc-mes-txt").textContent = mes(I.meses[i]);
    document.getElementById("calc-valor").textContent = SOL + num(valor, 2);
    var t = SOL + num(monto, 2) + " de " + mes(I.meses[i]) + " compran lo mismo que <strong>" + SOL + num(valor, 2) +
      "</strong> de dic. 2006.";
    if (i > 0) t += " Con un monto fijo, la transferencia perdió <strong>" + num(perdida, 1) + " %</strong> de su poder de compra." +
      " Para comprar lo mismo que en 2006, tendría que ser de " + SOL + num(monto * f, 2) + ".";
    document.getElementById("calc-texto").innerHTML = t;
    var fx;
    if (c === "pobres") {
      fx = "valor = monto ÷ [0,446 × A(mes) / A(dic. 2006) + 0,554 × R(mes) / R(dic. 2006)]<br>" +
        "= " + num(monto, 2) + " ÷ [0,446 × " + num(I.alimentos[i], 2) + " / " + num(I.alimentos[0], 2) + " + 0,554 × " +
        num(I.sin_alimentos[i], 2) + " / " + num(I.sin_alimentos[0], 2) + "]<br>A = IPC alimentos (PN39445PM), R = IPC sin alimentos (PN38706PM)";
    } else {
      var s = c === "total" ? I.total : I.alimentos, cod = c === "total" ? "PN38705PM" : "PN39445PM";
      fx = "valor = monto × IPC(dic. 2006) ÷ IPC(" + mes(I.meses[i]) + ")<br>= " + num(monto, 2) + " × " + num(s[0], 2) +
        " ÷ " + num(s[i], 2) + " &nbsp;(serie " + cod + ")";
    }
    document.getElementById("calc-formula").innerHTML = fx;
  }
  [cMonto, cMes, cCanasta].forEach(function (e) { e.addEventListener("input", calcular); });
  calcular();

  // ════════════════════════════════════════════════════════════════════════════════════════════════
  //  Hallazgo 2: gasto en alimentos
  // ════════════════════════════════════════════════════════════════════════════════════════════════
  barras(document.getElementById("g-alimentos"), {
    aria: "Barras: participación de los alimentos en el gasto de hogares pobres y no pobres",
    filas: [{ etiqueta: "Hogares pobres", valores: [D.enaho.alimentos.pobres] },
            { etiqueta: "Hogares no pobres", valores: [D.enaho.alimentos.no_pobres] }],
    series: [{ nombre: "Gasto en alimentos", color: "--s2" }], max: 50, sufijo: " %",
    aviso: function (f) { return "<b>" + f.etiqueta + "</b>" + num(f.valores[0], 1) + " % del gasto se va en alimentos"; },
  });

  // ════════════════════════════════════════════════════════════════════════════════════════════════
  //  Hallazgo 3: mapa + barras por departamento, y pobreza por grupos
  // ════════════════════════════════════════════════════════════════════════════════════════════════
  var nacional = D.enaho.nacional.pobreza;
  var deps = {};
  D.departamentos.forEach(function (d) { deps[d.id] = d; });
  function avisoDep(id) {
    var d = deps[id];
    return "<b>" + d.nombre + "</b>" + filaAviso("--s1", "Pobreza", num(d.valor, 1) + " %") +
      '<span class="fila" style="color:var(--tinta-2)">Referencia oficial<em>' + num(d.referencia, 1) + " %</em></span>" +
      '<span class="fila" style="color:var(--tinta-2)">Frente al país<em>' + (d.valor >= nacional ? "+" : "") +
      num(d.valor - nacional, 1) + " pts.</em></span>";
  }
  function filasDep(orden) {
    var lista = D.departamentos.slice();
    lista.sort(orden === "nombre" ? function (a, b) { return a.nombre.localeCompare(b.nombre, "es"); }
      : function (a, b) { return b.valor - a.valor; });
    return lista.map(function (d) { return { id: d.id, etiqueta: d.nombre, valores: [d.valor] }; });
  }
  var elMapa = null;
  var barrasDep = barras(document.getElementById("g-dep"), {
    aria: "Barras: pobreza por departamento, 2024",
    filas: filasDep("valor"), series: [{ nombre: "Pobreza", color: "--s1" }], max: 50, sufijo: " %",
    ref: { valor: nacional, etiqueta: "Perú " + num(nacional, 1) + " %" },
    aviso: function (f) { return avisoDep(f.id); },
    alResaltar: function (id) { if (elMapa) elMapa.resaltar(id); },
  });
  if (D.mapa) {
    var valores = {};
    D.departamentos.forEach(function (d) { valores[d.id] = d.valor; });
    elMapa = mapa(document.getElementById("g-mapa"), "ley-mapa", {
      mapa: D.mapa, valores: valores, vmax: 50, ref: nacional, aria: "Mapa del Perú por departamento coloreado según la pobreza",
      aviso: avisoDep, alResaltar: function (id) { barrasDep.resaltar(id); },
    });
  } else {
    document.getElementById("g-mapa").innerHTML = '<img src="mapas/pobreza_departamento_2024.png" alt="Mapa de pobreza por departamento, 2024">';
  }
  document.getElementById("orden-dep").addEventListener("click", function (ev) {
    var b = ev.target.closest("button");
    if (!b) return;
    this.querySelectorAll("button").forEach(function (x) { x.setAttribute("aria-pressed", x === b); });
    barrasDep.cambiar({ filas: filasDep(b.dataset.orden) });
  });

  var G = D.enaho.grupos;
  var SERIES_POBREZA = [{ nombre: "Pobreza", color: "--s1" }, { nombre: "Pobreza extrema", color: "--s2" }];
  function confGrupo(clave) {
    var filas = G[clave], conExtrema = filas.some(function (f) { return f.extrema !== null; });
    var series = conExtrema ? SERIES_POBREZA : SERIES_POBREZA.slice(0, 1);
    leyenda("ley-grupos", series);
    return {
      series: series,
      filas: filas.map(function (f) { return { etiqueta: f.etiqueta, valores: conExtrema ? [f.pobreza, f.extrema] : [f.pobreza] }; }),
    };
  }
  var inicial = confGrupo("hogar"), seriesActuales = inicial.series;
  var barrasGrupos = barras(document.getElementById("g-grupos"), {
    aria: "Barras: pobreza por grupo de hogares", filas: inicial.filas, series: inicial.series, max: 50, sufijo: " %",
    ref: { valor: nacional, etiqueta: "Perú " + num(nacional, 1) + " %" },
    aviso: function (f) {
      return "<b>" + f.etiqueta + "</b>" + f.valores.map(function (v, s) {
        return filaAviso(seriesActuales[s].color, seriesActuales[s].nombre, num(v, 1) + " %");
      }).join("");
    },
  });
  pestanas("pest-grupos", [["hogar", "Tipo de hogar"], ["area", "Área"], ["jefatura", "Jefatura del hogar"], ["sexo", "Sexo"]],
    function (clave) { var c = confGrupo(clave); seriesActuales = c.series; barrasGrupos.cambiar(c); });

  // ════════════════════════════════════════════════════════════════════════════════════════════════
  //  Hallazgo 4: cobertura de Juntos
  // ════════════════════════════════════════════════════════════════════════════════════════════════
  var NOMBRES_COB = { "Pobres": "Todos los pobres", "Pobres extremos": "Pobres extremos", "Pobres con menores de 5": "Pobres con niños menores de 5",
    "Pobres urbanos": "Pobres urbanos", "Pobres rurales": "Pobres rurales", "No pobres": "No pobres" };
  barras(document.getElementById("g-juntos"), {
    aria: "Barras: porcentaje de personas en hogares con Juntos por grupo",
    filas: D.cobertura_juntos.slice().sort(function (a, b) { return b.valor - a.valor; })
      .map(function (c) { return { etiqueta: NOMBRES_COB[c.etiqueta] || c.etiqueta, valores: [c.valor] }; }),
    series: [{ nombre: "Con Juntos", color: "--s3" }], max: 60, sufijo: " %",
    aviso: function (f) { return "<b>" + f.etiqueta + "</b>" + num(f.valores[0], 1) + " % vive en un hogar que recibe Juntos"; },
  });

  // ════════════════════════════════════════════════════════════════════════════════════════════════
  //  Evaluación: cifras y tabla
  // ════════════════════════════════════════════════════════════════════════════════════════════════
  var E = D.evaluacion;
  function resumenModo(modo) {
    var ok = E.filter(function (q) { return q[modo].resultado === "correcta"; }).length;
    var sin = E.filter(function (q) { return q[modo].valor === null; }).length;
    var seg = E.reduce(function (s, q) { return s + q[modo].segundos; }, 0) / E.length;
    return { ok: ok, sin: sin, seg: seg };
  }
  var a = resumenModo("A"), b = resumenModo("B");
  document.getElementById("eval-cifras").innerHTML =
    '<div class="cifra"><span style="margin:0 0 6px">Sin herramientas</span><b>' + a.ok + "/" + E.length + "</b><small>" +
    a.sin + " sin respuesta · " + num(a.seg, 1) + " s por pregunta</small></div>" +
    '<div class="cifra"><span style="margin:0 0 6px">Con MCP y Skills</span><b>' + b.ok + "/" + E.length + "</b><small>" +
    (E.length - b.ok - b.sin) + " errores · " + num(b.seg, 1) + " s por pregunta</small></div>";

  function conUnidad(v, unidad) {
    if (v === null) return "—";
    if (unidad.indexOf("soles") === 0) return SOL + num(v, 2);
    if (unidad === "puntos porcentuales") return num(v, 2) + " pp";
    return num(v, 2) + " %";
  }
  function celdaModo(r, unidad) {
    if (r.valor === null) return '<span class="estado no">— No responde</span>';
    var ok = r.resultado === "correcta";
    return '<span class="estado ' + (ok ? "ok" : "no") + '">' + (ok ? "✓ " : "✗ ") + conUnidad(r.valor, unidad) + "</span>";
  }
  function pintarTabla(tipo) {
    document.querySelector("#t-eval tbody").innerHTML = E.filter(function (q) { return tipo === "todas" || q.tipo === tipo; })
      .map(function (q) {
        var usadas = q.B.herramientas.filter(function (h) { return h !== "Skill" || !q.B.skills.length; }).concat(q.B.skills.map(function (s) { return "Skill " + s; }));
        return "<tr><td><details><summary>" + escapar(q.corta) + '<span class="chip">' + q.tipo + "</span></summary>" +
          '<p class="nota" style="margin-top:6px"><strong>Pregunta:</strong> ' + escapar(q.pregunta) + "</p>" +
          '<p class="nota"><strong>Sin herramientas:</strong> ' + escapar(q.A.fuente) + "</p>" +
          '<p class="nota"><strong>Con herramientas:</strong> ' + escapar(q.B.fuente) + "</p></details></td>" +
          '<td class="num">' + conUnidad(q.esperada, q.unidad) + "</td>" +
          "<td>" + celdaModo(q.A, q.unidad) + "</td><td>" + celdaModo(q.B, q.unidad) + "</td>" +
          '<td class="num">' + num(q.A.segundos, 1) + " → " + num(q.B.segundos, 1) + "</td>" +
          '<td class="herr">' + usadas.map(function (h) { return "<code>" + escapar(h) + "</code>"; }).join(" ") + "</td></tr>";
      }).join("");
  }
  pestanas("pest-eval", [["todas", "Todas"], ["BCRP", "BCRP"], ["ENAHO", "ENAHO"], ["Mixta", "Mixtas"]], pintarTabla);
  pintarTabla("todas");

  // ── Pie y botón de modo claro u oscuro ───────────────────────────────────────────────────────────
  document.getElementById("pie-generado").textContent = "Datos del sitio generados el " + D.generado.split("-").reverse().join("-") +
    " con scripts/construir_sitio.py, desde las salidas del proyecto y el servidor MCP bcrp.";
  document.querySelector(".tema").addEventListener("click", function () {
    var raiz = document.documentElement;
    var oscuro = raiz.dataset.theme ? raiz.dataset.theme === "dark" : matchMedia("(prefers-color-scheme: dark)").matches;
    raiz.dataset.theme = oscuro ? "light" : "dark";
    try { localStorage.setItem("tema", raiz.dataset.theme); } catch (e) {}
  });
})();
