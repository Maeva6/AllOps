/**
 * Générateur CER UCAC-ICAM — Style fidèle au document de référence
 */
const {
  Document, Packer, Paragraph, TextRun, Table, TableRow, TableCell,
  Header, Footer, AlignmentType, HeadingLevel, LevelFormat,
  BorderStyle, WidthType, ShadingType, VerticalAlign,
  PageNumber, PageBreak, TabStopType
} = require("docx");
const fs = require("fs");

const dataPath   = process.argv[2];
const outputPath = process.argv[3];
const cer        = JSON.parse(fs.readFileSync(dataPath, "utf8"));

const ROUGE="B40000",BLEU2="4F81BD",NOIR="000000",GRIS="595959",GRIS_CL="F2F2F2",BLANC="FFFFFF";
const PAGE_W=11906,PAGE_H=16838,MAR_T=1440,MAR_B=1440,MAR_L=1800,MAR_R=1440;
const CW=PAGE_W-MAR_L-MAR_R;

const brd=(c,s=4)=>({style:BorderStyle.SINGLE,size:s,color:c});
const bords=c=>({top:brd(c),bottom:brd(c),left:brd(c),right:brd(c)});
const noBrd={style:BorderStyle.NONE,size:0,color:BLANC};
const noBords={top:noBrd,bottom:noBrd,left:noBrd,right:noBrd};

function run(text,o={}){
  return new TextRun({text,font:o.font||"Calibri",size:o.size||22,
    bold:o.bold||false,italic:o.italic||false,color:o.color||NOIR,
    underline:o.underline?{}:undefined});
}
function para(runs,o={}){
  const children=Array.isArray(runs)?runs:[typeof runs==="string"?run(runs,o):runs];
  return new Paragraph({alignment:o.align||AlignmentType.LEFT,
    spacing:{before:o.before??80,after:o.after??80,line:o.line||276},
    indent:o.indent?{left:o.indent}:undefined,border:o.border||undefined,children});
}
const sp=(n=100)=>new Paragraph({spacing:{before:0,after:n},children:[]});

function md2paras(md,baseSize=22){
  if(!md)return[sp(80)];
  const lines=md.split("\n");
  const result=[];
  let inCode=false;
  let tableLines=[];

  function inline(text,sz){
    const parts=[];
    const re=/(\*\*[^*]+\*\*|\*[^*]+\*|`[^`]+`)/g;
    let last=0,m;
    while((m=re.exec(text))!==null){
      if(m.index>last)parts.push(run(text.slice(last,m.index),{size:sz}));
      const tok=m[0];
      if(tok.startsWith("**"))parts.push(run(tok.slice(2,-2),{size:sz,bold:true}));
      else if(tok.startsWith("*"))parts.push(run(tok.slice(1,-1),{size:sz,italic:true}));
      else parts.push(run(tok.slice(1,-1),{size:sz-2,font:"Courier New",color:"7030A0"}));
      last=m.index+tok.length;
    }
    if(last<text.length)parts.push(run(text.slice(last),{size:sz}));
    return parts.length?parts:[run(text,{size:sz})];
  }

  function flushTable(){
    if(!tableLines.length)return;
    const rows=tableLines.filter(l=>!/^\|[-\s|:]+\|$/.test(l));
    if(!rows.length){tableLines=[];return;}
    const allCells=rows.map(r=>r.split("|").slice(1,-1).map(c=>c.trim()));
    const nbCols=Math.max(...allCells.map(r=>r.length));
    const colW=Math.floor(CW/nbCols);
    result.push(new Table({
      width:{size:CW,type:WidthType.DXA},
      columnWidths:Array(nbCols).fill(colW),
      rows:allCells.map((row,ri)=>new TableRow({
        tableHeader:ri===0,
        children:Array.from({length:nbCols},(_,ci)=>new TableCell({
          borders:bords("BBBBBB"),
          width:{size:colW,type:WidthType.DXA},
          shading:{fill:ri===0?ROUGE:ri%2===0?"FFF0F0":BLANC,type:ShadingType.CLEAR},
          margins:{top:70,bottom:70,left:120,right:120},
          verticalAlign:VerticalAlign.CENTER,
          children:[para(inline(row[ci]||"",20),
            {before:0,after:0,align:ri===0?AlignmentType.CENTER:AlignmentType.LEFT})],
        })),
      })),
    }));
    result.push(sp(120));
    tableLines=[];
  }

  for(let i=0;i<lines.length;i++){
    const raw=lines[i];
    const line=raw.trim();
    if(line.startsWith("```")){
      flushTable();
      inCode=!inCode;
      if(!inCode)result.push(sp(80));
      continue;
    }
    if(inCode){
      result.push(new Paragraph({
        spacing:{before:0,after:0},
        shading:{fill:GRIS_CL,type:ShadingType.CLEAR},
        indent:{left:360,right:360},
        children:[run(raw||" ",{size:18,font:"Courier New",color:GRIS})],
      }));
      continue;
    }
    if(line.startsWith("|")){tableLines.push(line);continue;}
    else flushTable();
    if(!line){result.push(sp(80));continue;}
    if(line.startsWith("#### ")){
      result.push(new Paragraph({heading:HeadingLevel.HEADING_4,
        spacing:{before:160,after:80},children:inline(line.slice(5),baseSize)}));continue;}
    if(line.startsWith("### ")){
      result.push(new Paragraph({heading:HeadingLevel.HEADING_3,
        spacing:{before:200,after:100},children:inline(line.slice(4),baseSize+2)}));continue;}
    if(line.startsWith("## ")){
      result.push(new Paragraph({heading:HeadingLevel.HEADING_2,
        spacing:{before:240,after:120},children:inline(line.slice(3),baseSize+2)}));continue;}
    if(line.startsWith("# ")){
      result.push(new Paragraph({heading:HeadingLevel.HEADING_1,
        spacing:{before:280,after:140},children:inline(line.slice(2),baseSize+4)}));continue;}
    if(/^[-*+] /.test(line)){
      result.push(new Paragraph({numbering:{reference:"bullets",level:0},
        spacing:{before:40,after:40},children:inline(line.slice(2),baseSize)}));continue;}
    if(/^\d+\. /.test(line)){
      result.push(new Paragraph({numbering:{reference:"numbers",level:0},
        spacing:{before:40,after:40},
        children:inline(line.replace(/^\d+\.\s+/,""),baseSize)}));continue;}
    result.push(para(inline(line,baseSize),{before:60,after:60}));
  }
  flushTable();
  return result.length?result:[sp(80)];
}

// ── Page de garde — identique au document de référence ───────────────────────
function pageDGarde(){
  const date=new Date().toLocaleDateString("fr-FR");
  const items=[
    ["Étudiant : ",cer.etudiant],
    ["Pilote : ",cer.pilote],
    ["Co-pilote : ",cer.copilote],
    ["Promotion : ",cer.promotion],
    ["Année académique : ",cer.annee],
    ["Date : ",date],
  ].filter(([,v])=>v);

  return [
    para([run(cer.titre_prosit.toUpperCase(),{size:40,bold:true,color:ROUGE})],
      {align:AlignmentType.CENTER,before:1440,after:200}),
    para([run("Cahier d'Étude et de Recherche",{size:36,bold:true})],
      {align:AlignmentType.CENTER,before:0,after:600}),
    ...items.map(([label,val])=>para(
      [run(label,{bold:true,size:24}),run(val,{size:24})],
      {align:AlignmentType.CENTER,before:80,after:80}
    )),
    new Paragraph({spacing:{before:0,after:0},children:[new PageBreak()]}),
  ];
}

const h1=text=>new Paragraph({heading:HeadingLevel.HEADING_1,
  spacing:{before:480,after:120},
  children:[run(text,{size:28,bold:true,color:ROUGE})]});
const h2=text=>new Paragraph({heading:HeadingLevel.HEADING_2,
  spacing:{before:240,after:100},
  children:[run(text,{size:26,bold:true})]});

const docHeader=new Header({children:[new Paragraph({
  spacing:{before:0,after:80},border:{bottom:brd(ROUGE,6)},
  tabStops:[{type:TabStopType.RIGHT,position:CW}],
  children:[
    run(cer.titre_prosit.slice(0,55)+(cer.titre_prosit.length>55?"…":""),
      {size:18,italic:true,color:GRIS}),
    new TextRun({text:"\t",size:18}),
    run(cer.etudiant||"",{size:18,italic:true,color:GRIS}),
  ],
})]});

const docFooter=new Footer({children:[new Paragraph({
  alignment:AlignmentType.CENTER,spacing:{before:80,after:0},
  border:{top:brd(ROUGE,4)},
  children:[
    run("Page ",{size:18,color:GRIS}),
    new TextRun({children:[PageNumber.CURRENT],size:18,color:GRIS,font:"Calibri"}),
    run(" / ",{size:18,color:GRIS}),
    new TextRun({children:[PageNumber.TOTAL_PAGES],size:18,color:GRIS,font:"Calibri"}),
  ],
})]});

const plan=cer.plan||[];
const realisation=cer.realisation||{};

const body=[
  ...pageDGarde(),
  h1("I. Analyse du contexte"),
  ...md2paras(cer.contexte),sp(120),
  h1("II. Analyse des besoins"),
  h2("Besoins"),...md2paras(cer.besoins),
  h2("Contraintes"),...md2paras(cer.contraintes||"RAS"),sp(120),
  h1("III. Définition de la problématique"),
  ...md2paras(cer.problematique),sp(120),
  h1("IV. Plan d'action"),
  ...plan.map(etape=>new Paragraph({
    numbering:{reference:"numbers",level:0},
    spacing:{before:60,after:60},
    children:[run(etape,{size:22})],
  })),sp(120),
  h1("V. Réalisation du plan d'action"),
  ...plan.flatMap((etape,i)=>[
    h2(`V.${i+1} ${etape}`),
    ...md2paras(realisation[String(i)]||""),
    sp(100),
  ]),
  h1("VI. Validation des pistes de solutions"),
  ...md2paras(cer.validation),sp(120),
  h1("VII. Conclusion et retours sur les objectifs"),
  ...md2paras(cer.conclusion),sp(120),
  h1("VIII. Bilan critique du travail effectué"),
  ...md2paras(cer.bilan),sp(120),
  h1("IX. Synthèse des résultats obtenus"),
  ...md2paras(cer.synthese),sp(120),
  h1("X. Références bibliographiques"),
  ...md2paras(cer.references),
];

const doc=new Document({
  numbering:{config:[
    {reference:"bullets",levels:[{level:0,format:LevelFormat.BULLET,text:"\u2022",
      alignment:AlignmentType.LEFT,
      style:{run:{font:"Symbol",size:22},paragraph:{indent:{left:720,hanging:360}}}}]},
    {reference:"numbers",levels:[{level:0,format:LevelFormat.DECIMAL,text:"%1.",
      alignment:AlignmentType.LEFT,
      style:{paragraph:{indent:{left:720,hanging:360}}}}]},
  ]},
  styles:{
    default:{document:{run:{font:"Calibri",size:22}}},
    paragraphStyles:[
      {id:"Heading1",name:"Heading 1",basedOn:"Normal",next:"Normal",quickFormat:true,
        run:{size:28,bold:true,color:ROUGE,font:"Calibri"},
        paragraph:{spacing:{before:480,after:120},outlineLevel:0}},
      {id:"Heading2",name:"Heading 2",basedOn:"Normal",next:"Normal",quickFormat:true,
        run:{size:26,bold:true,color:BLEU2,font:"Calibri"},
        paragraph:{spacing:{before:240,after:100},outlineLevel:1}},
      {id:"Heading3",name:"Heading 3",basedOn:"Normal",next:"Normal",quickFormat:true,
        run:{size:24,bold:true,color:BLEU2,font:"Calibri"},
        paragraph:{spacing:{before:200,after:80},outlineLevel:2}},
      {id:"Heading4",name:"Heading 4",basedOn:"Normal",next:"Normal",quickFormat:true,
        run:{size:22,bold:true,italic:true,color:GRIS,font:"Calibri"},
        paragraph:{spacing:{before:160,after:80},outlineLevel:3}},
    ],
  },
  sections:[{
    properties:{page:{
      size:{width:PAGE_W,height:PAGE_H},
      margin:{top:MAR_T,bottom:MAR_B,left:MAR_L,right:MAR_R},
    }},
    headers:{default:docHeader},
    footers:{default:docFooter},
    children:body,
  }],
});

Packer.toBuffer(doc).then(buf=>{
  fs.writeFileSync(outputPath,buf);
  console.log("OK:"+outputPath);
}).catch(err=>{
  console.error("ERR:"+err.message);
  process.exit(1);
});
