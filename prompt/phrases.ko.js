// Korean wording only; rule code selects keys and supplies character-relative sides.
export const ko = {
 labels: ['인물', '앵글', '자세', '몸통', '팔', '다리', '체중', '시선'],
 genders: {female: '여성 인물, 전신', male: '남성 인물, 전신'},
 angles: {
  front: {label:'정면', phrase:'정면에서 바라본 전신'},
  side: {label:'옆', phrase:'인물의 오른쪽 옆에서 바라본 전신'},
  three_quarter: {label:'사선', phrase:'인물의 오른쪽 사선에서 바라본 전신'},
  high: {label:'위', phrase:'위에서 내려다본 전신'},
  low: {label:'아래', phrase:'아래에서 올려다본 전신'},
 },
 errors: {gender:'알 수 없는 성별입니다.', angle:'알 수 없는 앵글입니다.', id:'포즈와 카탈로그의 id가 다릅니다.'},
 sides: {l:'왼', r:'오른'},
 join: ', ',
 body: {
  forward:'상체를 앞으로 기울임', back:'상체를 뒤로 젖힘',
  left:'골반에 비해 몸통을 왼쪽으로 돌림', right:'골반에 비해 몸통을 오른쪽으로 돌림',
  tiltLeft:'몸통을 왼쪽으로 기울임', tiltRight:'몸통을 오른쪽으로 기울임', neutral:'몸통을 자연스럽게 세움',
 },
 arm: {
  high: s => `${s}팔을 높이 듦`, side: s => `${s}팔을 옆으로 듦`,
  forward: s => `${s}팔을 앞으로 둠`, back: s => `${s}팔을 뒤로 둠`,
  combine: (position, elbow) => elbow ? `${position.replace(/듦$/, '들고').replace(/둠$/, '두고')} ${elbow}` : position,
  neutral: s => `${s}팔을 몸 옆에 둠`, bent:'팔꿈치를 굽힘', straight:'팔꿈치를 거의 폄',
 },
 leg: {
  forward: s => `${s}허벅지를 앞으로 기울이고 무릎을 굽힘`,
  extended: s => `${s}다리를 앞으로 뻗고 무릎을 거의 폄`,
  bent: s => `${s}무릎을 굽힘`, straight: s => `${s}다리는 무릎을 거의 폄`,
  outward: s => `${s}다리를 옆으로 벌림`, neutral: s => `${s}다리를 자연스럽게 둠`,
 },
 weight: {
  seated:'골반을 낮춘 앉은 자세로, 지지점의 하중 비율은 특정하지 않음',
  uncertain:'관절 회전만으로 체중 분배와 접지 여부를 특정하기 어려움',
  left:'왼쪽을 지지 중심으로 둔 자세로 추정', right:'오른쪽을 지지 중심으로 둔 자세로 추정',
 },
 gaze: {
  up:'몸통에 비해 고개를 듦', down:'몸통에 비해 고개를 숙임',
  left:'몸통에 비해 고개를 왼쪽으로 돌림', right:'몸통에 비해 고개를 오른쪽으로 돌림',
  tiltLeft:'고개를 왼쪽으로 기울임', tiltRight:'고개를 오른쪽으로 기울임', neutral:'몸통 방향을 따라 자연스럽게 앞을 봄',
 },
};
