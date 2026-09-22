import { StatusBar } from 'expo-status-bar'
import { useEffect, useRef, useState } from 'react'
import NetInfo from '@react-native-community/netinfo'
import { AppState, Alert, Pressable, SafeAreaView, ScrollView, StyleSheet, Text, TextInput, View } from 'react-native'
import * as Location from 'expo-location'
import * as ImagePicker from 'expo-image-picker'
import { Audio } from 'expo-av'
import { Ionicons } from '@expo/vector-icons'
import AsyncStorage from '@react-native-async-storage/async-storage'
import { InterviewGuide } from './components/native-interview-guide'
import { clearStoredAuthToken, enqueueSubmission, flushPendingSubmissions, getStatistics, getStoredAuthSession, getStoredAuthToken, getCurrentUser, login, readPendingSubmissions, storeAuthSession, type AuthSession, type SubmissionStatistics } from './api'

type ViewKey = 'Inicio' | 'Entrevistados' | 'Grupo RAP' | 'Panel admin'
type Form = { code: string; title: string; description: string; stage: string }
export type Interviewee = { id: string; name: string; role: string; organization: string }

const forms: Form[] = [
  { code: 'ENT', title: 'Entrevista semiestructurada', description: 'Guía por actor con preguntas núcleo y repreguntas editables.', stage: 'Campo' },
  { code: 'OBS', title: 'Observación etnográfica', description: 'Escena, actores, materiales y reflexividad.', stage: 'Campo' },
  { code: 'REC', title: 'Recorrido comentado', description: 'GPS, paradas, notas y exportación.', stage: 'Campo' },
  { code: 'MEM', title: 'Muro cronológico', description: 'Hitos editables y memoria colectiva.', stage: 'Poscampo' },
]

const initialInterviewees: Interviewee[] = [
  { id: 'alcalde', name: 'Alcalde / autoridad local', role: 'Autoridad local', organization: 'Municipalidad' },
  { id: 'directivo', name: 'Directivo de institución', role: 'Directivo', organization: 'Institución educativa' },
]

export default function App() {
  const [session, setSession] = useState<AuthSession | null>(null)
  const [sessionReady, setSessionReady] = useState(false)
  const [view, setView] = useState<ViewKey>('Inicio')
  useEffect(() => {
    let active = true
    getStoredAuthSession().then(async (stored) => {
      if (!stored) { if (active) setSessionReady(true); return }
      try {
        const user = await getCurrentUser(stored.token)
        if (active) setSession({ ...stored, user })
      } catch { await clearStoredAuthToken() }
      finally { if (active) setSessionReady(true) }
    }).catch(() => { if (active) setSessionReady(true) })
    return () => { active = false }
  }, [])
  if (!sessionReady) return <SafeAreaView style={styles.safe}><View style={styles.loading}><Text style={styles.brand}>AYNI</Text><Text style={styles.subtitle}>Comprobando sesión…</Text></View></SafeAreaView>
  if (!session) return <AuthScreen onAuthenticated={(next) => setSession(next)} />
  const signOut = async () => { await clearStoredAuthToken(); setSession(null) }
  const [selectedForm, setSelectedForm] = useState<Form | null>(null)
  const [interviewees, setInterviewees] = useState(initialInterviewees)
  const [selectedInterviewee, setSelectedInterviewee] = useState(initialInterviewees[0].id)
  const [hydrated, setHydrated] = useState(false)
  useEffect(() => {
    AsyncStorage.getItem('ayni.interviewees').then((saved) => {
      if (saved) setInterviewees(JSON.parse(saved))
      setHydrated(true)
    }).catch(() => setHydrated(true))
  }, [])
  useEffect(() => {
    if (hydrated) AsyncStorage.setItem('ayni.interviewees', JSON.stringify(interviewees)).catch(() => undefined)
  }, [interviewees, hydrated])
  if (selectedForm) return <NativeForm form={selectedForm} onBack={() => setSelectedForm(null)} interviewees={interviewees} selectedInterviewee={selectedInterviewee} onIntervieweeChange={setSelectedInterviewee} />
  return <SafeAreaView style={styles.safe}><StatusBar style="dark" /><View style={styles.shell}><Header user={session.user} onSignOut={signOut} /><ScrollView contentContainerStyle={styles.content}><Text style={styles.eyebrow}>PROYECTO ACTIVO · AYNA — AGOSTO 2026</Text><Text style={styles.title}>Buenos días, María</Text><Text style={styles.subtitle}>Elige un instrumento según el momento del trabajo.</Text><View style={styles.nav}>{(['Inicio', 'Entrevistados', 'Grupo RAP', 'Panel admin'] as ViewKey[]).map((item) => <Pressable key={item} onPress={() => setView(item)} style={[styles.navItem, view === item && styles.navActive]}><Text style={styles.navText}>{item}</Text></Pressable>)}</View>{view === 'Inicio' && <Home onOpen={setSelectedForm} />}{view === 'Entrevistados' && <IntervieweeManager interviewees={interviewees} onAdd={(person) => setInterviewees((items) => [...items, person])} onDelete={(id) => setInterviewees((items) => items.filter((person) => person.id !== id))} />}{view === 'Grupo RAP' && <Rap />}{view === 'Panel admin' && <Admin />}</ScrollView></View></SafeAreaView>
}

function AuthScreen({ onAuthenticated }: { onAuthenticated: (session: AuthSession) => void }) {
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const submit = async () => {
    if (!email.trim() || !password) return setError('Ingresa tu correo y contraseña.')
    setBusy(true); setError('')
    try { const session = await login(email, password); await storeAuthSession(session); onAuthenticated(session) }
    catch (cause) { setError(cause instanceof Error ? cause.message : 'No fue posible iniciar sesión.') }
    finally { setBusy(false) }
  }
  return <SafeAreaView style={styles.safe}><View style={styles.auth}><View style={styles.brandMark}><Ionicons name="leaf-outline" size={24} color="#fff" /></View><Text style={styles.authTitle}>Iniciar sesión</Text><Text style={styles.subtitle}>Accede a tus instrumentos y sincroniza el trabajo de campo.</Text><Input label="Correo electrónico" value={email} onChangeText={setEmail} /><Input label="Contraseña" value={password} onChangeText={setPassword} secureTextEntry /><Text style={styles.error}>{error}</Text><Pressable style={styles.primaryButton} onPress={submit} disabled={busy}><Text style={styles.primaryText}>{busy ? 'Conectando…' : 'Entrar'}</Text></Pressable></View></SafeAreaView>
}

function Header({ user, onSignOut }: { user: AuthSession['user']; onSignOut: () => void }) { return <View style={styles.header}><View style={styles.brandMark}><Ionicons name="leaf-outline" size={22} color="#fff" /></View><View><Text style={styles.brand}>AYNI</Text><Text style={styles.brandSub}>Investigación situada</Text></View><View style={styles.headerRight}><Text style={styles.user}>{user.name.slice(0, 2).toUpperCase()}</Text><Pressable onPress={onSignOut}><Text style={styles.dangerText}>Salir</Text></Pressable></View></View> }
function Home({ onOpen }: { onOpen: (form: Form) => void }) { return <><Pressable style={styles.primaryButton} onPress={() => onOpen(forms[0])}><Text style={styles.primaryText}>+ Nueva recolección</Text></Pressable><Text style={styles.sectionTitle}>Instrumentos de recolección</Text><View style={styles.grid}>{forms.map((form) => <View key={form.code} style={styles.card}><View style={styles.cardRow}><Text style={styles.code}>{form.code}</Text><Text style={styles.stage}>{form.stage}</Text></View><Text style={styles.cardTitle}>{form.title}</Text><Text style={styles.cardDesc}>{form.description}</Text><Pressable style={styles.outlineButton} onPress={() => onOpen(form)}><Text style={styles.outlineText}>Abrir instrumento</Text></Pressable></View>)}</View></> }
function IntervieweeManager({ interviewees, onAdd, onDelete }: { interviewees: Interviewee[]; onAdd: (person: Interviewee) => void; onDelete: (id: string) => void }) { const [name, setName] = useState(''); const [role, setRole] = useState(''); const [organization, setOrganization] = useState(''); return <><Text style={styles.sectionTitle}>Directorio de entrevistados</Text><Text style={styles.subtitle}>Añade perfiles disponibles para la guía ENT.</Text><View style={styles.card}><Input label="Nombre o identificador" value={name} onChangeText={setName} /><Input label="Rol o perfil" value={role} onChangeText={setRole} /><Input label="Organización" value={organization} onChangeText={setOrganization} /><Pressable style={styles.primaryButton} onPress={() => { if (!name.trim() || !role.trim()) return; onAdd({ id: `${Date.now()}`, name, role, organization: organization || 'Sin organización' }); setName(''); setRole(''); setOrganization('') }}><Text style={styles.primaryText}>+ Añadir entrevistado</Text></Pressable></View>{interviewees.map((person) => <View key={person.id} style={styles.listRow}><View><Text style={styles.cardTitle}>{person.name}</Text><Text style={styles.cardDesc}>{person.role} · {person.organization}</Text></View><View style={styles.personActions}><Text style={styles.status}>Disponible</Text><Pressable onPress={() => onDelete(person.id)}><Text style={styles.dangerText}>Eliminar</Text></Pressable></View></View>)}</> }
function Rap() { const [tasks, setTasks] = useState<{ text: string; type: string }[]>([]); const [reflection, setReflection] = useState(''); const [text, setText] = useState(''); const [type, setType] = useState('Qué observar'); const [loaded, setLoaded] = useState(false); useEffect(() => { AsyncStorage.getItem('ayni.rap.tasks').then((saved) => { if (saved) setTasks(JSON.parse(saved)); setLoaded(true) }).catch(() => setLoaded(true)) }, []); useEffect(() => { if (loaded) AsyncStorage.setItem('ayni.rap.tasks', JSON.stringify(tasks)).catch(() => undefined) }, [tasks, loaded]); return <><Text style={styles.sectionTitle}>Grupo RAP</Text><Text style={styles.cardDesc}>Objetivo central: comprender cómo se organiza la vida cotidiana en Ayna.</Text><View style={styles.card}><Text style={styles.cardTitle}>Checklist para mañana</Text><Input label="¿Qué nos obliga a pensar?" value={reflection} onChangeText={setReflection} multiline /><Input label="Nueva tarea para mañana" value={text} onChangeText={setText} /><View style={styles.segment}>{['Qué observar', 'A quién preguntar', 'Qué documentar'].map((item) => <Pressable key={item} onPress={() => setType(item)} style={[styles.segmentItem, type === item && styles.segmentActive]}><Text style={styles.segmentText}>{item}</Text></Pressable>)}</View><Pressable style={styles.primaryButton} onPress={() => { if (text.trim()) { setTasks([...tasks, { text, type }]); setText('') } }}><Text style={styles.primaryText}>+ Añadir tarea</Text></Pressable></View>{tasks.map((task, index) => <View key={index} style={styles.listRow}><Text style={styles.cardDesc}>{task.type}: {task.text}</Text></View>)}</> }
function Admin() {
  const [stats, setStats] = useState<SubmissionStatistics | null>(null)
  const [error, setError] = useState('')
  useEffect(() => { getStoredAuthToken().then((token) => token ? getStatistics(token).then(setStats).catch((cause) => setError(cause instanceof Error ? cause.message : 'No fue posible cargar las métricas.')) : setError('Sesión no disponible.')) }, [])
  return <><Text style={styles.sectionTitle}>Panel de administración</Text>{error ? <Text style={styles.error}>{error}</Text> : null}<View style={styles.stats}><Stat label="Enviados" value={stats ? String(stats.submitted_count) : '—'} /><Stat label="Borradores" value={stats ? String(stats.draft_count) : '—'} /><Stat label="Total" value={stats ? String(stats.total_submissions) : '—'} /></View><View style={styles.card}><Text style={styles.cardTitle}>Preparación de campo</Text><Text style={styles.cardDesc}>Las métricas provienen del servidor autenticado.</Text><Text style={styles.cardDesc}>{stats ? `${stats.by_form_type.length} tipos de instrumento registrados` : 'Cargando métricas…'}</Text></View></>
}
function Stat({ label, value }: { label: string; value: string }) { return <View style={styles.stat}><Text style={styles.statValue}>{value}</Text><Text style={styles.cardDesc}>{label}</Text></View> }
function NativeForm({ form, onBack, interviewees, selectedInterviewee, onIntervieweeChange }: { form: Form; onBack: () => void; interviewees: Interviewee[]; selectedInterviewee: string; onIntervieweeChange: (id: string) => void }) {
  const [location, setLocation] = useState('Solicitando ubicación…')
  const [locationError, setLocationError] = useState('')
  const [pendingCount, setPendingCount] = useState(0)
  const [syncMessage, setSyncMessage] = useState('Sin borradores pendientes de sincronización')
  useEffect(() => {
    let active = true
    void (async () => {
      try {
        const permission = await Location.requestForegroundPermissionsAsync()
        if (!active) return
        if (!permission.granted) return setLocation('Ubicación no autorizada')
        const result = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced })
        if (active) { setLocation(`${result.coords.latitude.toFixed(5)}, ${result.coords.longitude.toFixed(5)}`); setLocationError('') }
      } catch (cause) {
        if (active) { setLocation('Ubicación no disponible'); setLocationError(cause instanceof Error ? cause.message : 'No se pudo obtener la ubicación.') }
      }
    })()
    return () => { active = false }
  }, [])
  useEffect(() => {
    let active = true
    const refreshSync = async (online: boolean) => {
      if (online) { try { await flushPendingSubmissions() } catch (cause) { console.error('[ayni] queue flush failed', cause) } }
      const pending = await readPendingSubmissions()
      if (active) { setPendingCount(pending.length); setSyncMessage(pending.find((item) => item.lastError)?.lastError ?? (pending.length ? `${pending.length} borrador(es) pendiente(s) de sincronización` : 'Sin borradores pendientes de sincronización')) }
    }
    NetInfo.fetch().then((state) => refreshSync(Boolean(state.isConnected && state.isInternetReachable !== false)))
    const unsubscribe = NetInfo.addEventListener((state) => { void refreshSync(Boolean(state.isConnected && state.isInternetReachable !== false)) })
    return () => { active = false; unsubscribe() }
  }, [])
  const saveDraft = async () => {
    const token = await getStoredAuthToken()
    await enqueueSubmission(form.code, { location, savedAt: new Date().toISOString() }, token ?? undefined)
    try { await flushPendingSubmissions() } catch (cause) { console.error('[ayni] manual queue flush failed', cause) }
    const pending = await readPendingSubmissions()
    setPendingCount(pending.length)
    const latestFailure = pending.find((item) => item.lastError)?.lastError
    setSyncMessage(latestFailure ? `Pendiente: ${latestFailure}` : pending.length ? `${pending.length} borrador(es) pendiente(s) de sincronización` : 'Sin borradores pendientes de sincronización')
    Alert.alert('Guardado', pending.length ? 'Borrador guardado localmente y pendiente de sincronización.' : 'Borrador guardado y sincronizado.')
  }
  return <SafeAreaView style={styles.safe}><View style={styles.formHeader}><Pressable onPress={onBack}><Text style={styles.back}>‹ Volver</Text></Pressable><View><Text style={styles.formCode}>{form.code}</Text><Text style={styles.formTitle}>{form.title}</Text></View></View><ScrollView contentContainerStyle={styles.content}>{form.code === 'ENT' && <InterviewGuide interviewees={interviewees} selectedInterviewee={selectedInterviewee} onIntervieweeChange={onIntervieweeChange} />}{form.code === 'MEM' ? <Timeline /> : form.code === 'REC' ? <Route /> : form.code === 'OBS' ? <><Input label="Lugar o unidad observada" /><Input label="Actores presentes" /><Input label="Descripción densa" multiline /><Input label="Reflexividad del investigador" multiline /><MediaCapture /></> : null}<View style={styles.card}><Text style={styles.cardTitle}>Datos automáticos</Text><Text style={styles.cardDesc}>GPS: {location}</Text>{locationError ? <Text style={styles.error}>{locationError}</Text> : null}<Text style={styles.cardDesc}>Fecha y hora: {new Date().toLocaleString()}</Text></View><View style={styles.draftBar}><Ionicons name="cloud-offline-outline" size={18} color="#1e664a" /><Text style={styles.cardDesc}>Borrador guardado localmente; se sincronizará cuando haya conexión.</Text></View><Pressable style={styles.primaryButton} onPress={saveDraft}><Text style={styles.primaryText}>Guardar borrador</Text></Pressable><View style={styles.draftBar}><Ionicons name={pendingCount ? 'cloud-upload-outline' : 'cloud-done-outline'} size={18} color="#1e664a" /><Text style={styles.cardDesc}>{syncMessage}</Text></View></ScrollView></SafeAreaView>
}

function Route() {
  const [stops, setStops] = useState<{ latitude: number; longitude: number; timestamp: string }[]>([])
  const [position, setPosition] = useState('GPS en espera')
  const [loaded, setLoaded] = useState(false)
  const [permissionMessage, setPermissionMessage] = useState('')
  const watchRef = useRef<Location.LocationSubscription | null>(null)
  const startTracking = async () => {
    const permission = await Location.getForegroundPermissionsAsync()
    if (!permission.granted) { setPermissionMessage('Autoriza la ubicación para iniciar el recorrido.'); return }
    watchRef.current?.remove()
    try {
      watchRef.current = await Location.watchPositionAsync({ accuracy: Location.Accuracy.Balanced, distanceInterval: 5, timeInterval: 10000 }, ({ coords }) => setPosition(`${coords.latitude.toFixed(5)}, ${coords.longitude.toFixed(5)}`))
      setPermissionMessage('')
    } catch (cause) {
      setPosition('GPS no disponible')
      setPermissionMessage(cause instanceof Error ? cause.message : 'No se pudo iniciar el GPS.')
    }
  }
  useEffect(() => {
    let active = true
    AsyncStorage.getItem('ayni.route.stops').then((saved) => { if (active && saved) setStops(JSON.parse(saved)); if (active) setLoaded(true) }).catch(() => { if (active) setLoaded(true) })
    const onAppState = (nextState: string) => { if (nextState !== 'active') { watchRef.current?.remove(); watchRef.current = null; setPosition('GPS pausado en segundo plano') } else { void startTracking() } }
    const subscription = AppState.addEventListener('change', onAppState)
    void startTracking()
    return () => { active = false; subscription.remove(); watchRef.current?.remove(); watchRef.current = null }
  }, [])
  useEffect(() => { if (loaded) AsyncStorage.setItem('ayni.route.stops', JSON.stringify(stops)).catch(() => undefined) }, [stops, loaded])
  const addStop = async () => { const permission = await Location.getForegroundPermissionsAsync(); if (!permission.granted) return setPermissionMessage('Autoriza la ubicación antes de registrar una parada.'); try { const result = await Location.getCurrentPositionAsync({ accuracy: Location.Accuracy.Balanced }); setStops((items) => [...items, { latitude: result.coords.latitude, longitude: result.coords.longitude, timestamp: new Date().toISOString() }]); setPermissionMessage('') } catch { setPermissionMessage('No se pudo obtener una ubicación. Inténtalo de nuevo.') } }
  return <><View style={styles.card}><Text style={styles.cardTitle}>Recorrido activo · GPS</Text><Text style={styles.cardDesc}>El GPS se pausa cuando la app queda en segundo plano para proteger batería y privacidad.</Text><Text style={styles.cardDesc}>Mapa offline · {stops.length} paradas</Text><Text style={styles.status}>{position}</Text>{permissionMessage ? <Text style={styles.error}>{permissionMessage}</Text> : null}<Pressable style={styles.primaryButton} onPress={addStop}><Text style={styles.primaryText}>Registrar parada</Text></Pressable></View>{stops.map((stop, index) => <View key={stop.timestamp} style={styles.listRow}><View><Text style={styles.cardTitle}>Parada {index + 1}</Text><Text style={styles.cardDesc}>{stop.latitude.toFixed(5)}, {stop.longitude.toFixed(5)}</Text></View><Text style={styles.cardDesc}>{new Date(stop.timestamp).toLocaleTimeString()}</Text></View>)}</>
}
function Timeline() { const [notes, setNotes] = useState<{ title: string; detail: string }[]>([]); const [selected, setSelected] = useState<number | null>(null); const [loaded, setLoaded] = useState(false); useEffect(() => { AsyncStorage.getItem('ayni.timeline.notes').then((saved) => { if (saved) setNotes(JSON.parse(saved)); setLoaded(true) }).catch(() => setLoaded(true)) }, []); useEffect(() => { if (loaded) AsyncStorage.setItem('ayni.timeline.notes', JSON.stringify(notes)).catch(() => undefined) }, [notes, loaded]); const add = () => { setNotes((items) => [...items, { title: '', detail: '' }]); setSelected(notes.length) }; const remove = (index: number) => { setNotes((items) => items.filter((_, i) => i !== index)); setSelected(null) }; return <><View style={styles.timeline}><View style={styles.timelineLine} />{notes.map((note, index) => <Pressable key={index} onPress={() => setSelected(index)} style={[styles.timelineNote, selected === index && styles.pickerSelected]}><TextInput style={styles.timelineInput} value={note.title} onChangeText={(value) => setNotes((items) => items.map((item, i) => i === index ? { ...item, title: value } : item))} placeholder="Título del hito" /><Text style={styles.cardDesc}>Toca para editar la historia</Text><Pressable onPress={() => remove(index)}><Text style={styles.dangerText}>Eliminar hito</Text></Pressable></Pressable>)}</View><Pressable style={styles.outlineButton} onPress={add}><Text style={styles.outlineText}>+ Nuevo post-it</Text></Pressable>{selected !== null && <View style={styles.card}><Text style={styles.cardTitle}>Historia profunda</Text><TextInput style={[styles.input, styles.multiline]} multiline value={notes[selected].detail} onChangeText={(value) => setNotes((items) => items.map((item, i) => i === selected ? { ...item, detail: value } : item))} placeholder="Qué ocurrió y por qué importa..." /></View>}</> }
function MediaCapture() {
  const [consent, setConsent] = useState(false)
  const [imageUri, setImageUri] = useState<string | null>(null)
  const [recording, setRecording] = useState<Audio.Recording | null>(null)
  const recordingRef = useRef<Audio.Recording | null>(null)
  const [audioUri, setAudioUri] = useState<string | null>(null)
  const [lifecycleMessage, setLifecycleMessage] = useState('')
  const [mediaBusy, setMediaBusy] = useState(false)
  useEffect(() => {
    const stopRecording = async () => {
      const current = recordingRef.current
      if (!current) return
      try { await current.stopAndUnloadAsync() } catch (cause) { console.error('[ayni] audio cleanup failed', cause) }
      recordingRef.current = null
      setRecording(null)
      await Audio.setAudioModeAsync({ allowsRecordingIOS: false, playsInSilentModeIOS: true }).catch(() => undefined)
    }
    const subscription = AppState.addEventListener('change', (nextState) => {
      if (nextState !== 'active' && recordingRef.current) { setLifecycleMessage('La grabación se detuvo al salir de la app.'); void stopRecording() }
    })
    return () => { subscription.remove(); void stopRecording() }
  }, [])
  const captureImage = async () => {
    if (mediaBusy) return
    if (!consent) return Alert.alert('Consentimiento requerido', 'Confirma el consentimiento antes de capturar evidencia.')
    setMediaBusy(true); setLifecycleMessage('')
    try {
      const permission = await ImagePicker.requestCameraPermissionsAsync()
      if (!permission.granted) return Alert.alert('Permiso requerido', 'Activa el acceso a la cámara para continuar.')
      const result = await ImagePicker.launchCameraAsync({ mediaTypes: ['images'], quality: 0.7 })
      if (!result.canceled && result.assets[0]?.uri) setImageUri(result.assets[0].uri)
    } catch (cause) {
      setLifecycleMessage(cause instanceof Error ? cause.message : 'No se pudo capturar la fotografía.')
    } finally { setMediaBusy(false) }
  }
  const toggleRecording = async () => {
    if (mediaBusy) return
    if (!consent) return Alert.alert('Consentimiento requerido', 'Confirma el consentimiento antes de grabar audio.')
    setMediaBusy(true); setLifecycleMessage('')
    try {
      if (recordingRef.current) {
        const current = recordingRef.current
        const uri = current.getURI()
        await current.stopAndUnloadAsync()
        recordingRef.current = null; setAudioUri(uri); setRecording(null)
        await Audio.setAudioModeAsync({ allowsRecordingIOS: false, playsInSilentModeIOS: true })
        return
      }
      const permission = await Audio.requestPermissionsAsync()
      if (!permission.granted) return Alert.alert('Permiso requerido', 'Activa el acceso al micrófono para continuar.')
      await Audio.setAudioModeAsync({ allowsRecordingIOS: true, playsInSilentModeIOS: true })
      const result = await Audio.Recording.createAsync(Audio.RecordingOptionsPresets.HIGH_QUALITY)
      recordingRef.current = result.recording; setRecording(result.recording)
    } catch (cause) {
      setLifecycleMessage(cause instanceof Error ? cause.message : 'No se pudo gestionar la grabación.')
      recordingRef.current = null; setRecording(null)
      await Audio.setAudioModeAsync({ allowsRecordingIOS: false, playsInSilentModeIOS: true }).catch(() => undefined)
    } finally { setMediaBusy(false) }
  }
  return <View style={styles.card}><Text style={styles.cardTitle}>Multimedia y consentimiento</Text><Text style={styles.cardDesc}>La evidencia solo se captura después de confirmar el consentimiento.</Text>{lifecycleMessage ? <Text style={styles.error}>{lifecycleMessage}</Text> : null}<Pressable style={styles.outlineButton} onPress={captureImage} disabled={mediaBusy}><Text style={styles.outlineText}>{mediaBusy ? 'Procesando…' : imageUri ? 'Tomar otra fotografía' : 'Abrir cámara'}</Text></Pressable>{imageUri && <Text style={styles.status}>Fotografía capturada</Text>}<Pressable style={styles.outlineButton} onPress={toggleRecording} disabled={mediaBusy}><Text style={styles.outlineText}>{mediaBusy ? 'Procesando…' : recording ? 'Detener grabación' : audioUri ? 'Grabar nuevo audio' : 'Grabar audio'}</Text></Pressable>{audioUri && <Text style={styles.status}>Audio capturado</Text>}<Pressable style={styles.consentRow} onPress={() => setConsent((value) => !value)}><View style={[styles.checkbox, consent && styles.checkboxActive]}>{consent && <Text style={styles.checkmark}>✓</Text>}</View><Text style={styles.cardDesc}>Confirmo que existe consentimiento para esta evidencia.</Text></Pressable></View>
}

function Input({ label, value, onChangeText, multiline = false, secureTextEntry = false }: { label: string; value?: string; onChangeText?: (text: string) => void; multiline?: boolean; secureTextEntry?: boolean }) { return <View><Text style={styles.label}>{label}</Text><TextInput value={value} onChangeText={onChangeText} multiline={multiline} secureTextEntry={secureTextEntry} autoCapitalize="none" style={[styles.input, multiline && styles.multiline]} placeholderTextColor="#87919b" /></View> }

const styles = StyleSheet.create({ safe: { flex: 1, backgroundColor: '#f7f8f5' }, loading: { flex: 1, alignItems: 'center', justifyContent: 'center', gap: 12 }, auth: { flex: 1, justifyContent: 'center', padding: 24, gap: 14 }, authTitle: { color: '#173d2e', fontSize: 28, fontWeight: '800' }, error: { minHeight: 20, color: '#a53d36', fontSize: 13 }, shell: { flex: 1 }, header: { minHeight: 76, paddingHorizontal: 20, flexDirection: 'row', alignItems: 'center', gap: 12, backgroundColor: '#f7f8f5', borderBottomWidth: 1, borderBottomColor: '#dde3dc' }, brandMark: { width: 38, height: 38, borderRadius: 12, alignItems: 'center', justifyContent: 'center', backgroundColor: '#1e664a' }, brand: { fontWeight: '800', letterSpacing: 2, color: '#173d2e' }, brandSub: { color: '#718079', fontSize: 11 }, headerRight: { marginLeft: 'auto' }, user: { color: '#1e664a', fontWeight: '800' }, content: { padding: 20, gap: 16, paddingBottom: 40 }, eyebrow: { color: '#1e664a', fontSize: 11, fontWeight: '700', letterSpacing: 1 }, title: { color: '#173d2e', fontSize: 28, fontWeight: '800' }, subtitle: { color: '#68756d', fontSize: 15, lineHeight: 21 }, nav: { flexDirection: 'row', gap: 8, marginVertical: 4 }, navItem: { paddingHorizontal: 12, paddingVertical: 9, borderRadius: 20, backgroundColor: '#e9eee9' }, navActive: { backgroundColor: '#1e664a' }, navText: { color: '#173d2e', fontSize: 12, fontWeight: '700' }, card: { padding: 16, gap: 12, backgroundColor: '#fff', borderWidth: 1, borderColor: '#dde3dc', borderRadius: 16 }, grid: { gap: 12 }, cardRow: { flexDirection: 'row', justifyContent: 'space-between' }, code: { color: '#1e664a', fontWeight: '800', letterSpacing: 1 }, stage: { color: '#68756d', fontSize: 12 }, cardTitle: { color: '#173d2e', fontSize: 16, fontWeight: '700' }, cardDesc: { color: '#68756d', fontSize: 13, lineHeight: 19 }, primaryButton: { minHeight: 48, paddingHorizontal: 16, borderRadius: 12, backgroundColor: '#1e664a', alignItems: 'center', justifyContent: 'center' }, primaryText: { color: '#fff', fontWeight: '700' }, outlineButton: { minHeight: 44, paddingHorizontal: 14, borderRadius: 10, borderWidth: 1, borderColor: '#c9d5ca', alignItems: 'center', justifyContent: 'center' }, outlineText: { color: '#1e664a', fontWeight: '700' }, listRow: { padding: 15, borderRadius: 12, borderWidth: 1, borderColor: '#dde3dc', backgroundColor: '#fff', flexDirection: 'row', justifyContent: 'space-between', gap: 10 }, status: { color: '#1e664a', fontSize: 12, fontWeight: '700' }, sectionTitle: { color: '#173d2e', fontSize: 21, fontWeight: '800' }, label: { color: '#4d5e53', fontSize: 12, fontWeight: '700', marginBottom: 6 },   personActions: { alignItems: 'flex-end', gap: 6 },
  draftBar: { flexDirection: 'row', alignItems: 'center', gap: 8, padding: 12, borderRadius: 10, backgroundColor: '#e8f0e8' }, dangerText: { color: '#a53d36', fontWeight: '700', marginTop: 8 },
  consentRow: { flexDirection: 'row', alignItems: 'flex-start', gap: 10, paddingTop: 4 }, checkbox: { width: 22, height: 22, borderRadius: 6, borderWidth: 1, borderColor: '#9caf9e', alignItems: 'center', justifyContent: 'center' }, checkboxActive: { backgroundColor: '#1e664a', borderColor: '#1e664a' }, checkmark: { color: '#fff', fontWeight: '800' },
  input: { minHeight: 46, borderWidth: 1, borderColor: '#c9d5ca', borderRadius: 10, paddingHorizontal: 12, color: '#173d2e', backgroundColor: '#fff' }, multiline: { minHeight: 100, paddingTop: 12, textAlignVertical: 'top' }, segment: { flexDirection: 'row', flexWrap: 'wrap', gap: 6 }, segmentItem: { padding: 10, borderRadius: 10, backgroundColor: '#edf1ec' }, segmentActive: { backgroundColor: '#cfe5d6' }, segmentText: { color: '#315440', fontSize: 12 }, stats: { flexDirection: 'row', gap: 10 }, stat: { flex: 1, padding: 15, borderRadius: 14, backgroundColor: '#e8f0e8' }, statValue: { color: '#1e664a', fontSize: 24, fontWeight: '800' }, formHeader: { minHeight: 72, paddingHorizontal: 16, flexDirection: 'row', alignItems: 'center', gap: 18, borderBottomWidth: 1, borderBottomColor: '#dde3dc', backgroundColor: '#fff' }, back: { color: '#1e664a', fontWeight: '700' }, formCode: { color: '#1e664a', fontSize: 11, fontWeight: '800', letterSpacing: 1 }, formTitle: { color: '#173d2e', fontWeight: '700' }, pickerWrap: { gap: 6 }, pickerItem: { padding: 12, borderRadius: 9, backgroundColor: '#f0f3ef' }, pickerSelected: { backgroundColor: '#cfe5d6', borderWidth: 1, borderColor: '#1e664a' }, timeline: { minHeight: 250, padding: 20, gap: 18, position: 'relative' }, timelineLine: { position: 'absolute', left: 25, right: 25, top: 50, height: 2, backgroundColor: '#1e664a' }, timelineNote: { padding: 14, marginTop: 20, borderRadius: 14, borderWidth: 1, borderColor: '#c9d5ca', backgroundColor: '#fff' }, timelineInput: { color: '#173d2e', fontWeight: '700', borderBottomWidth: 1, borderBottomColor: '#dde3dc', paddingVertical: 6 } })
