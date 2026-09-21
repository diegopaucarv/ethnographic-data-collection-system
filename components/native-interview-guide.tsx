import { useState } from 'react'
import { Pressable, Text, TextInput, View } from 'react-native'
import type { Interviewee } from '../App'

const coreQuestions = [
  '¿Cómo se enteró y qué fue lo primero que decidió?',
  '¿Qué cambió después de esa decisión?',
  '¿Quiénes participaron y qué tensiones aparecieron?',
]

export function InterviewGuide({ interviewees, selectedInterviewee, onIntervieweeChange }: { interviewees: Interviewee[]; selectedInterviewee: string; onIntervieweeChange: (id: string) => void }) {
  const [questions, setQuestions] = useState(coreQuestions)
  const [notes, setNotes] = useState<Record<number, string>>({})
  const [followUps, setFollowUps] = useState<Record<number, string[]>>({})
  const addFollowUp = (index: number) => setFollowUps((items) => ({ ...items, [index]: [...(items[index] ?? []), ''] }))
  const updateFollowUp = (questionIndex: number, followUpIndex: number, value: string) => setFollowUps((items) => ({ ...items, [questionIndex]: (items[questionIndex] ?? []).map((item, index) => index === followUpIndex ? value : item) }))
  return <View style={{ gap: 14 }}><View style={styles.card}><Text style={styles.label}>Entrevistado</Text><View style={styles.pickerWrap}>{interviewees.map((person) => <Pressable key={person.id} onPress={() => onIntervieweeChange(person.id)} style={[styles.pickerItem, selectedInterviewee === person.id && styles.pickerSelected]}><Text style={styles.cardDesc}>{person.name}</Text><Text style={styles.small}>{person.role} · {person.organization}</Text></Pressable>)}</View></View>{questions.map((question, index) => <View key={index} style={styles.card}><Text style={styles.cardTitle}>Pregunta {index + 1}{index === 0 ? ' · Núcleo' : ''}</Text><TextInput value={question} onChangeText={(value) => setQuestions((items) => items.map((item, itemIndex) => itemIndex === index ? value : item))} style={styles.input} /><TextInput value={notes[index] ?? ''} onChangeText={(value) => setNotes((items) => ({ ...items, [index]: value }))} multiline placeholder="Notas y frases textuales..." style={[styles.input, styles.multiline]} /><Pressable style={styles.outlineButton} onPress={() => addFollowUp(index)}><Text style={styles.outlineText}>+ Añadir repregunta</Text></Pressable>{(followUps[index] ?? []).map((followUp, followUpIndex) => <TextInput key={followUpIndex} value={followUp} onChangeText={(value) => updateFollowUp(index, followUpIndex, value)} placeholder={`Repregunta ${followUpIndex + 1}`} style={styles.input} />)}</View>)}</View>
}

const styles = { card: { padding: 16, gap: 12, backgroundColor: '#fff', borderWidth: 1, borderColor: '#dde3dc', borderRadius: 16 }, label: { color: '#68756d', fontSize: 12, fontWeight: '700' as const }, pickerWrap: { gap: 8 }, pickerItem: { padding: 12, borderRadius: 10, backgroundColor: '#edf1ec' }, pickerSelected: { backgroundColor: '#cfe5d6', borderWidth: 1, borderColor: '#1e664a' }, cardDesc: { color: '#68756d', fontSize: 13, lineHeight: 19 }, small: { color: '#87919b', fontSize: 11 }, cardTitle: { color: '#173d2e', fontSize: 16, fontWeight: '700' as const }, input: { minHeight: 46, borderWidth: 1, borderColor: '#c9d5ca', borderRadius: 10, paddingHorizontal: 12, color: '#173d2e', backgroundColor: '#fff' }, multiline: { minHeight: 100, paddingTop: 12, textAlignVertical: 'top' as const }, outlineButton: { minHeight: 44, paddingHorizontal: 14, borderRadius: 10, borderWidth: 1, borderColor: '#c9d5ca', alignItems: 'center' as const, justifyContent: 'center' as const }, outlineText: { color: '#1e664a', fontWeight: '700' as const } }
