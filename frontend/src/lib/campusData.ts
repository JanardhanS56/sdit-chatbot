export interface CampusEvent {
  name: string
  month: string
  months: number[]
  description: string
  type: 'academic' | 'technical' | 'cultural' | 'community' | 'sports'
}

export const campusEvents: CampusEvent[] = [
  { name: 'Orientation Programme', month: 'September', months: [8], description: 'Welcome programme covering campus, policies, facilities, and faculty.', type: 'academic' },
  { name: 'Krishna Janmashtami', month: 'August / September', months: [7, 8], description: 'Cultural celebration with bhajans, skits, and traditional games.', type: 'cultural' },
  { name: 'Blood Donation Camp', month: 'September / October', months: [8, 9], description: 'Community health initiative organised with local health organisations.', type: 'community' },
  { name: 'Samshodhan', month: 'October / November', months: [9, 10], description: 'Technical project exhibition with models, prototypes, and external judges.', type: 'technical' },
  { name: 'SURABHI', month: 'November / December', months: [10, 11], description: 'Intra-college cultural and technical competitions.', type: 'cultural' },
  { name: 'Technospark', month: 'January', months: [0], description: 'State-level science model exhibition for discoveries and technology solutions.', type: 'technical' },
  { name: 'Annual Sports Meet', month: 'February', months: [1], description: 'Track, field, and team sports across departments.', type: 'sports' },
  { name: 'Shree Devi Sambhram', month: 'March', months: [2], description: 'National-level cultural and technical fest with performances and competitions.', type: 'cultural' },
  { name: 'Alumni Meet', month: 'April', months: [3], description: 'Networking and mentorship between alumni, students, and faculty.', type: 'community' },
  { name: 'Annual Day', month: 'May', months: [4], description: 'Year-end celebration of academic achievements and student talent.', type: 'cultural' },
  { name: 'Graduation and Farewell Day', month: 'May / June', months: [4, 5], description: 'Degree ceremonies, awards, and farewell celebrations for graduating students.', type: 'academic' },
]

export const personalizationOptions = {
  year: ['First year', 'Second year', 'Third year', 'Final year', 'Postgraduate'],
  department: ['CSE / AI', 'ECE', 'Mechanical', 'Civil / Aeronautical', 'MBA / MCA', 'Undecided'],
  interest: ['Coding and technology', 'Business and finance', 'Communication and leadership', 'Arts and culture', 'Sports and fitness', 'Social impact and sustainability'],
  goal: ['Build skills', 'Find a club', 'Prepare for placements', 'Explore events', 'Meet people and lead'],
}
