'use client'

import { useState } from 'react'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Separator } from '@/components/ui/separator'
import { Textarea } from '@/components/ui/textarea'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { Camera, Check, ChevronRight, ClipboardList, Clock3, Eye, FileText, HelpCircle, LayoutDashboard, MapPin, Menu, Mic, Plus, Search, Settings, Users, WifiOff } from 'lucide-react'

const forms = [
  { code: 'ETN', title: 'Ficha de escena etnográfica', description: 'Registra una escena con contexto, participantes y reflexividad.', count: '12 campos', tone: 'bg-primary' },
  { code: 'OBS', title: 'Jornada de observación', description: 'Identifica el lugar, horario, posición y actividad principal.', count: '9 campos', tone: 'bg-emerald-600' },
  { code: 'REC', title: 'Registro de escenas', description: 'Anota descripciones densas, frases e interpretaciones.', count: '5 columnas', tone: 'bg-amber-600' },
  { code: 'MEM', title: 'Memo analítico', description: 'Cierra la jornada con hallazgos y preguntas emergentes.', count: '8 campos', tone: 'bg-violet-600' },
]

const recent = [
  { code: 'ETN-014', title: 'Escena etnográfica', author: 'María González', date: 'Hoy, 10:42', status: 'Sincronizado' },
  { code: 'OBS-008', title: 'Jornada de observación', author: 'Carlos Ruiz', date: 'Ayer, 16:15', status: 'Sincronizado' },
  { code: 'REC-021', title: 'Registro de escenas', author: 'Ana Torres', date: 'Ayer, 13:08', status: 'Solo lectura' },
]

export function FieldDashboard() {
  const [activeView, setActiveView] = useState('Inicio')
  const [showForm, setShowForm] = useState(false)
  const [selectedForm, setSelectedForm] = useState(forms[0])
  const [saved, setSaved] = useState(false)

  if (showForm) {
    return <CollectionForm form={selectedForm} onBack={() => setShowForm(false)} saved={saved} onSave={() => setSaved(true)} />
  }

  return (
    <div className="min-h-screen bg-muted/30 text-foreground">
      <header className="sticky top-0 z-20 border-b bg-background/95 backdrop-blur">
        <div className="mx-auto flex h-18 max-w-[1500px] items-center justify-between px-4 sm:px-6 lg:px-8">
          <div className="flex items-center gap-3">
            <button className="rounded-lg p-2 text-muted-foreground hover:bg-muted lg:hidden" aria-label="Abrir menú"><Menu /></button>
            <div className="flex size-10 items-center justify-center rounded-xl bg-primary text-primary-foreground"><ClipboardList /></div>
            <div><p className="text-lg font-bold tracking-tight">Ayni Campo</p><p className="text-xs text-muted-foreground">Recolección cualitativa</p></div>
          </div>
          <div className="flex items-center gap-3"><Badge variant="outline" className="hidden gap-1.5 px-3 py-1.5 text-xs font-medium sm:flex"><WifiOff data-icon="inline-start" /> Trabajo sin conexión</Badge><div className="flex size-10 items-center justify-center rounded-full bg-secondary text-sm font-semibold">MG</div></div>
        </div>
      </header>
      <div className="mx-auto flex max-w-[1500px]">
        <aside className="hidden w-64 shrink-0 border-r bg-background lg:block"><nav className="flex flex-col gap-1 p-4" aria-label="Navegación principal">
          {[['Inicio', LayoutDashboard], ['Mis formularios', FileText], ['Registros del equipo', Users], ['Configuración', Settings]].map(([label, Icon]) => <button key={label as string} onClick={() => setActiveView(label as string)} className={`flex items-center gap-3 rounded-lg px-4 py-3 text-left text-sm font-medium transition-colors ${activeView === label ? 'bg-primary/10 text-primary' : 'text-muted-foreground hover:bg-muted hover:text-foreground'}`}><Icon className="size-5" />{label as string}</button>)}
        </nav><Separator /><div className="p-5"><div className="flex items-start gap-3 rounded-xl bg-secondary/60 p-4"><HelpCircle className="mt-0.5 size-5 shrink-0 text-primary" /><div><p className="text-sm font-semibold">¿Necesitas ayuda?</p><p className="mt-1 text-xs leading-5 text-muted-foreground">Consulta la guía de campo o contacta al coordinador.</p></div></div></div></aside>
        <main className="min-w-0 flex-1 p-4 sm:p-6 lg:p-10">
          <div className="mx-auto max-w-6xl">
            <div className="mb-8 flex flex-col justify-between gap-5 sm:flex-row sm:items-end"><div><p className="mb-2 text-sm font-medium text-primary">Proyecto activo · Ayna — Agosto 2026</p><h1 className="text-3xl font-bold tracking-tight sm:text-4xl">Buenos días, María</h1><p className="mt-2 text-base text-muted-foreground">Continúa tu recolección o revisa los registros del equipo.</p></div><Button size="lg" className="h-12 gap-2 px-5" onClick={() => { setSelectedForm(forms[0]); setShowForm(true) }}><Plus data-icon="inline-start" />Nueva recolección</Button></div>
            <div className="mb-10 grid gap-4 sm:grid-cols-3"><Stat icon={ClipboardList} label="Mis registros" value="24" note="3 esta semana" /><Stat icon={Users} label="Equipo" value="8" note="6 activos hoy" /><Stat icon={Clock3} label="Pendientes" value="3" note="Listos para sincronizar" /></div>
            <section><div className="mb-4 flex items-center justify-between"><div><h2 className="text-xl font-bold">Formularios de campo</h2><p className="mt-1 text-sm text-muted-foreground">Selecciona un instrumento para comenzar.</p></div><button className="hidden items-center gap-1 text-sm font-medium text-primary sm:flex">Ver todos <ChevronRight className="size-4" /></button></div><div className="grid gap-4 sm:grid-cols-2 xl:grid-cols-4">{forms.map((form) => <Card key={form.code} className="group border-border/70 shadow-sm transition-all hover:-translate-y-0.5 hover:shadow-md"><CardHeader><div className="mb-2 flex items-center justify-between"><div className={`flex size-11 items-center justify-center rounded-xl text-sm font-bold text-white ${form.tone}`}>{form.code}</div><Badge variant="secondary">{form.count}</Badge></div><CardTitle className="text-lg leading-snug">{form.title}</CardTitle><CardDescription className="min-h-10 leading-5">{form.description}</CardDescription></CardHeader><CardContent><Button variant="outline" className="w-full" onClick={() => { setSelectedForm(form); setShowForm(true) }}>Comenzar <ChevronRight data-icon="inline-end" /></Button></CardContent></Card>)}</div></section>
            <section className="mt-10"><div className="mb-4 flex items-center justify-between"><div><h2 className="text-xl font-bold">Registros recientes</h2><p className="mt-1 text-sm text-muted-foreground">Consulta los formularios enviados por todo el equipo.</p></div><div className="relative hidden sm:block"><Search className="absolute left-3 top-2.5 size-4 text-muted-foreground" /><Input className="h-9 w-56 pl-9" placeholder="Buscar registro" aria-label="Buscar registro" /></div></div><Card className="overflow-hidden border-border/70 shadow-sm"><div className="divide-y">{recent.map((item) => <div key={item.code} className="flex flex-col gap-3 p-4 sm:flex-row sm:items-center sm:justify-between sm:px-5"><div className="flex items-center gap-4"><div className="flex size-10 items-center justify-center rounded-lg bg-secondary"><FileText className="size-5 text-muted-foreground" /></div><div><p className="font-semibold">{item.title} <span className="ml-2 font-mono text-xs font-normal text-muted-foreground">{item.code}</span></p><p className="mt-1 text-sm text-muted-foreground">{item.author} · {item.date}</p></div></div><div className="flex items-center gap-3 pl-14 sm:pl-0"><Badge variant={item.status === 'Sincronizado' ? 'default' : 'secondary'} className="gap-1.5"><Check className="size-3.5" />{item.status}</Badge><Button variant="ghost" size="sm"><Eye data-icon="inline-start" />Ver</Button></div></div>)}</div></Card></section>
          </div>
        </main>
      </div>
    </div>
  )
}

function Stat({ icon: Icon, label, value, note }: { icon: typeof ClipboardList; label: string; value: string; note: string }) { return <Card className="border-border/70 shadow-sm"><CardContent className="flex items-center gap-4 p-5"><div className="flex size-11 items-center justify-center rounded-xl bg-primary/10 text-primary"><Icon className="size-5" /></div><div><p className="text-sm text-muted-foreground">{label}</p><div className="flex items-baseline gap-2"><p className="text-2xl font-bold">{value}</p><p className="text-xs text-muted-foreground">{note}</p></div></div></CardContent></Card> }

function CollectionForm({ form, onBack, saved, onSave }: { form: typeof forms[number]; onBack: () => void; saved: boolean; onSave: () => void }) {
  return <div className="min-h-screen bg-muted/30"><header className="sticky top-0 z-20 border-b bg-background/95 backdrop-blur"><div className="mx-auto flex h-18 max-w-4xl items-center justify-between px-4 sm:px-6"><Button variant="ghost" onClick={onBack}>← Volver</Button><div className="text-center"><p className="font-semibold">Nueva recolección</p><p className="text-xs text-muted-foreground">Guardado automático activado</p></div><Badge variant="outline" className="hidden sm:flex">Borrador</Badge></div></header><main className="mx-auto max-w-4xl p-4 sm:p-8"><div className="mb-8"><p className="mb-2 text-sm font-medium text-primary">{form.code}-015 · Paso 1 de 3</p><h1 className="text-3xl font-bold tracking-tight">{form.title}</h1><p className="mt-2 text-muted-foreground">Completa los datos principales. Los campos con * son obligatorios.</p><div className="mt-5 h-2 overflow-hidden rounded-full bg-secondary"><div className="h-full w-1/3 rounded-full bg-primary" /></div></div>{saved && <div className="mb-5 rounded-xl border border-emerald-200 bg-emerald-50 p-4 text-sm font-medium text-emerald-800">Borrador guardado correctamente. Puedes continuar cuando quieras.</div>}<div className="flex flex-col gap-5"><Card><CardHeader><CardTitle>Identificación de la escena</CardTitle><CardDescription>Cuéntanos dónde y cuándo ocurrió.</CardDescription></CardHeader><CardContent className="flex flex-col gap-5"><div className="grid gap-5 sm:grid-cols-2"><div><Label htmlFor="date">Fecha *</Label><Input id="date" type="date" className="mt-2 h-12" /></div><div><Label htmlFor="time">Hora de inicio *</Label><Input id="time" type="time" className="mt-2 h-12" /></div></div><div><Label htmlFor="place">Lugar o servicio *</Label><Input id="place" placeholder="Ej. Centro de salud de Ayna" className="mt-2 h-12" /></div><div><Label htmlFor="people">Personas presentes</Label><Textarea id="people" placeholder="Nombres, roles o descripción de participantes" className="mt-2 min-h-24" /></div></CardContent></Card><Card><CardHeader><CardTitle>Descripción densa</CardTitle><CardDescription>Registra lo observado con tus propias palabras.</CardDescription></CardHeader><CardContent><Textarea placeholder="Describe la escena, el ambiente y lo que está ocurriendo..." className="min-h-36 text-base" /><div className="mt-4 flex flex-wrap gap-2"><Button variant="outline" size="sm"><Mic data-icon="inline-start" />Añadir audio</Button><Button variant="outline" size="sm"><Camera data-icon="inline-start" />Tomar foto</Button><Button variant="outline" size="sm"><MapPin data-icon="inline-start" />Ubicar en mapa</Button></div></CardContent></Card><Card><CardHeader><CardTitle>Pregunta emergente</CardTitle><CardDescription>Añade una repregunta cuando el flujo de la conversación lo necesite.</CardDescription></CardHeader><CardContent><Button variant="outline" className="h-12 w-full border-dashed"><Plus data-icon="inline-start" />Añadir repregunta</Button></CardContent></Card></div><div className="mt-7 flex flex-col-reverse gap-3 sm:flex-row sm:justify-end"><Button variant="outline" size="lg" onClick={onBack}>Guardar y salir</Button><Button size="lg" onClick={onSave}>Continuar <ChevronRight data-icon="inline-end" /></Button></div></main></div>
}

export function AdminHint() { return <div className="sr-only">Los administradores pueden crear, editar y eliminar proyectos, formularios, preguntas, usuarios y registros.</div> }
