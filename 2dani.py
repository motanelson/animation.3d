# board3d_anim.py
# Requisitos: PyOpenGL, PyOpenGL_accelerate, freeglut
from OpenGL.GL import *
from OpenGL.GLU import *
from OpenGL.GLUT import *
import sys

# ------- configurações -------
GRID_SIZE = 16        # dimensão visual do tabuleiro (16x16)
CELL = 1.0
SPHERE_RADIUS = 0.25
CAM_DISTANCE = 22.0

FRAME_MS = 2000       # intervalo entre frames em ms (2000 == 2s)
AUTOPLAY = True       # se False, começa pausado

window_width = 1000
window_height = 800

# estado da animação
frames = []           # lista de frames; cada frame é matriz [row][col] (strings)
num_frames = 0
frame_w = 0
frame_h = 0
current_frame = 0
playing = AUTOPLAY

# posição do utilizador (índices grid)
user_x = GRID_SIZE // 2
user_y = GRID_SIZE // 2

# ------- Funções de load/compactação (adaptadas do teu ficheiro) -------
import zlib
def load_compressed(filename):
    """Carrega .xytb e devolve a string descompactada."""
    with open(filename, "rb") as f:
        compressed = f.read()
    return zlib.decompress(compressed).decode("utf-8")

def loads_from_text(texts):
    """
    Converte o texto (formato usado no teu .xytb: frames separados por ';', linhas por '\n', células por ',')
    em (ti, yi, xi, a) onde a[t][y][x] é string.
    """
    ll = True
    a = []
    ttt = texts.split(";")
    ti = len(ttt)
    yi = 0
    xi = 0
    for t in range(ti):
        yyy = ttt[t].strip().split("\n")
        yi = len(yyy)
        for y in range(yi):
            xxx = yyy[y].split(",")
            xi = len(xxx)
            if ll:
                # inicializa a[t][y][x]
                a = [[[" " for _ in range(xi)] for _ in range(yi)] for _ in range(ti)]
                ll = False
            for x in range(xi):
                b = xxx[x].strip()
                a[t][y][x] = b if b != "" else " "
    return ti, yi, xi, a

# ------- utilidade: converte índices de grelha -> coordenadas mundo (centro da célula) -------
def world_pos_from_index(ix, iy, grid_size=GRID_SIZE, cell=CELL):
    HALF = grid_size * cell / 2.0
    wx = -HALF + (cell / 2.0) + ix * cell
    wz = -HALF + (cell / 2.0) + iy * cell
    return wx, wz

# ------- OpenGL init e desenho (xadrezado) -------
def init_gl():
    glClearColor(1.0, 1.0, 0.6, 1.0)  # fundo amarelo
    glEnable(GL_DEPTH_TEST)
    glEnable(GL_NORMALIZE)
    glShadeModel(GL_SMOOTH)
    glEnable(GL_LIGHTING)
    glEnable(GL_LIGHT0)
    glLightfv(GL_LIGHT0, GL_POSITION, [5.0, 10.0, 5.0, 1.0])
    glLightfv(GL_LIGHT0, GL_DIFFUSE, [0.9, 0.9, 0.9, 1.0])
    glLightfv(GL_LIGHT0, GL_SPECULAR, [0.6, 0.6, 0.6, 1.0])

def draw_checkboard(grid_size=GRID_SIZE, cell=CELL):
    """Desenha tabuleiro tipo xadrez (cada célula é um quad) — sem iluminação para cores planas."""
    glDisable(GL_LIGHTING)
    half = (grid_size - 1) * cell / 2.0
    glBegin(GL_QUADS)
    for iy in range(grid_size):
        for ix in range(grid_size):
            wx = -half + ix * cell
            wz = -half + iy * cell
            if (ix + iy) % 2 == 0:
                glColor3f(0.85, 0.85, 0.85)
            else:
                glColor3f(0.65, 0.65, 0.65)
            glVertex3f(wx, 0.0, wz)
            glVertex3f(wx + cell, 0.0, wz)
            glVertex3f(wx + cell, 0.0, wz + cell)
            glVertex3f(wx, 0.0, wz + cell)
    glEnd()
    glEnable(GL_LIGHTING)

def draw_frame_spheres(frame):
    """Desenha esferas azuis onde frame[y][x] não for ' ' (vazio)."""
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [0.2, 0.2, 0.2, 1.0])
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 30.0)
    # assumimos frame é lista de lines: frame[linha][col]
    rows = min(GRID_SIZE, len(frame))
    for iy in range(rows):
        cols = min(GRID_SIZE, len(frame[iy]))
        for ix in range(cols):
            if str(frame[iy][ix]).strip() != "":
                wx, wz = world_pos_from_index(ix, iy)
                glPushMatrix()
                glTranslatef(wx, SPHERE_RADIUS, wz)
                glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, [0.0, 0.12, 0.9, 1.0])
                glutSolidSphere(SPHERE_RADIUS, 20, 20)
                glPopMatrix()

def draw_user_sphere():
    wx, wz = world_pos_from_index(user_x, user_y)
    glPushMatrix()
    glTranslatef(wx, SPHERE_RADIUS, wz)
    glMaterialfv(GL_FRONT_AND_BACK, GL_AMBIENT_AND_DIFFUSE, [0.95, 0.15, 0.15, 1.0])
    glMaterialfv(GL_FRONT_AND_BACK, GL_SPECULAR, [0.9, 0.9, 0.9, 1.0])
    glMaterialf(GL_FRONT_AND_BACK, GL_SHININESS, 60.0)
    glutSolidSphere(SPHERE_RADIUS * 1.15, 24, 24)
    glPopMatrix()

# ------- display / camera -------
rot = 0.0
ANGLE = 35.0
vertical_offset = -5.0  # quanto baixar o tabuleiro para o fundo do ecrã

def display():
    global rot
    glClear(GL_COLOR_BUFFER_BIT | GL_DEPTH_BUFFER_BIT)
    glMatrixMode(GL_MODELVIEW)
    glLoadIdentity()

    eye_y = CAM_DISTANCE * 0.5
    eye_x = 0.0
    eye_z = CAM_DISTANCE
    gluLookAt(eye_x, eye_y, eye_z, 0.0, 0.0, 0.0, 0.0, 1.0, 0.0)

    glRotatef(-ANGLE, 1.0, 0.0, 0.0)
    glRotatef(rot, 0.0, 1.0, 0.0)

    glPushMatrix()
    glTranslatef(0.0, vertical_offset, 0.0)

    # chão amarelo grande por baixo
    glDisable(GL_LIGHTING)
    glColor3f(1.0, 1.0, 0.6)
    half = GRID_SIZE * CELL / 2.0 + 6.0
    glBegin(GL_QUADS)
    glVertex3f(-half, -0.002, -half)
    glVertex3f(half, -0.002, -half)
    glVertex3f(half, -0.002, half)
    glVertex3f(-half, -0.002, half)
    glEnd()
    glEnable(GL_LIGHTING)

    # tabuleiro xadrez
    draw_checkboard()

    # desenhar frame actual
    if num_frames > 0:
        draw_frame_spheres(frames[current_frame])

    # esfera do utilizador
    draw_user_sphere()

    glPopMatrix()
    glutSwapBuffers()
    rot += 0.2

# ------- animação por timer (não usar time.sleep) -------
def timer_func(value):
    global current_frame
    if playing and num_frames > 0:
        current_frame = (current_frame + 1) % num_frames
        glutPostRedisplay()
    glutTimerFunc(FRAME_MS, timer_func, 0)

# ------- input: setas, pausar / sair -------
def special_key(key, x, y):
    global user_x, user_y
    if key == GLUT_KEY_LEFT:
        user_x = max(0, user_x - 1)
    elif key == GLUT_KEY_RIGHT:
        user_x = min(GRID_SIZE - 1, user_x + 1)
    elif key == GLUT_KEY_UP:
        user_y = max(0, user_y - 1)
    elif key == GLUT_KEY_DOWN:
        user_y = min(GRID_SIZE - 1, user_y + 1)
    glutPostRedisplay()

def keyboard(key, x, y):
    global playing
    if key == b'\x1b' or key == b'q':
        sys.exit(0)
    elif key == b' ':
        playing = not playing   # espaço pausa/continua
    elif key == b'<' and num_frames>0:
        # retrocede um frame
        global current_frame
        current_frame = (current_frame - 1) % num_frames
        glutPostRedisplay()
    elif key == b'>' and num_frames>0:
        current_frame = (current_frame + 1) % num_frames
        glutPostRedisplay()

def reshape(w, h):
    global window_width, window_height
    window_width = w
    window_height = h
    glViewport(0, 0, w, h)
    glMatrixMode(GL_PROJECTION)
    glLoadIdentity()
    gluPerspective(45.0, float(w) / float(h if h > 0 else 1), 0.1, 100.0)
    glMatrixMode(GL_MODELVIEW)

# ------- main: carrega .xytb e inicia GLUT -------
def main():
    global frames, num_frames, frame_w, frame_h, current_frame, playing

    # tenta carregar saida.xytb (mesmo ficheiro que usas no script de texto)
    try:
        text = load_compressed("saida.xytb")
        ti, yi, xi, a = loads_from_text(text)
        num_frames = ti
        frame_h = yi
        frame_w = xi
        frames = a
        print("Frames carregados:", num_frames, " Frame size:", frame_w, "x", frame_h)
    except Exception as e:
        print("Falha a carregar saida.xytb:", e)
        # cria frames vazios (1 frame vazio)
        num_frames = 1
        frames = [[[" " for _ in range(GRID_SIZE)] for _ in range(GRID_SIZE)]]

    glutInit(sys.argv)
    glutInitDisplayMode(GLUT_DOUBLE | GLUT_RGB | GLUT_DEPTH)
    glutInitWindowSize(window_width, window_height)
    glutCreateWindow(b"Tabuleiro 3D ")
    init_gl()
    glutDisplayFunc(display)
    glutReshapeFunc(reshape)
    glutSpecialFunc(special_key)
    glutKeyboardFunc(keyboard)
    glutTimerFunc(FRAME_MS, timer_func, 0)  # inicia timer
    glutIdleFunc(glutPostRedisplay)
    glutMainLoop()

if __name__ == "__main__":
    main()
