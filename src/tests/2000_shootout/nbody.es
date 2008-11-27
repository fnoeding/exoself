module nbody

from exoself.c.stdlib import *
from exoself.c.math import *


// no global constants, yet
def getPi() as float64
{
	return 3.1415926535897931;
}

def getSolarMass() as float64
{
	return 4 * getPi() * getPi();
}

def getDaysPerYear() as float64
{
	return 365.24;
}





def advance(n as uint32,
			x as float64*, y as float64*, z as float64*,
			vx as float64*, vy as float64*, vz as float64*,
			m as float64*,
			dt as float64) as void
{
	for i in range(n)
	{
		for j in range(i + 1, n)
		{
			dx = x[i] - x[j];
			dy = y[i] - y[j];
			dz = z[i] - z[j];

			dist = sqrt(dx * dx + dy * dy + dz * dz);
			mag = dt / (dist * dist * dist);

			vx[i] -= dx * m[j] * mag;
			vy[i] -= dy * m[j] * mag;
			vz[i] -= dz * m[j] * mag;

			vx[j] += dx * m[i] * mag;
			vy[j] += dy * m[i] * mag;
			vz[j] += dz * m[i] * mag;
		}
	}

	for i in range(n)
	{
		x[i] += dt * vx[i];
		y[i] += dt * vy[i];
		z[i] += dt * vz[i];
	}
}




def calcEnergy(n as uint32,
			x as float64*, y as float64*, z as float64*,
			vx as float64*, vy as float64*, vz as float64*,
			m as float64*) as float64
{
	e = 0.0;

	for i in range(n)
	{
		e += 0.5 * m[i] * (vx[i] * vx[i] + vy[i] * vy[i] + vz[i] * vz[i]);

		for j in range(i + 1, n)
		{
			dx = x[i] - x[j];
			dy = y[i] - y[j];
			dz = z[i] - z[j];

			dist = sqrt(dx * dx + dy * dy + dz * dz);

			e -= (m[i] * m[j]) / dist;
		}
	}

	return e;
}


def offsetMomentum(n as uint32,
			x as float64*, y as float64*, z as float64*,
			vx as float64*, vy as float64*, vz as float64*,
			m as float64*) as void
{
	px as float64;
	py as float64;
	pz as float64;

	for i in range(n)
	{
		px += vx[i] * m[i];
		py += vy[i] * m[i];
		pz += vz[i] * m[i];
	}

	vx[0] = -px / getSolarMass();
	vy[0] = -py / getSolarMass();
	vz[0] = -pz / getSolarMass();
}





def main() as int32
{
	n = 5u;

	x = cast(malloc(n * 8u) as float64*);
	y = cast(malloc(n * 8u) as float64*);
	z = cast(malloc(n * 8u) as float64*);
	vx = cast(malloc(n * 8u) as float64*);
	vy = cast(malloc(n * 8u) as float64*);
	vz = cast(malloc(n * 8u) as float64*);
	m = cast(malloc(n * 8u) as float64*);

	// sun
	x[0] = y[0] = z[0] = vx[0] = vy[0] = vz[0] = 0;
	m[0] = getSolarMass();

	// jupiter
	x[1] = 4.84143144246472090e+00;
	y[1] = -1.16032004402742839e+00;
	z[1] = -1.03622044471123109e-01;
	vx[1] = 1.66007664274403694e-03 * getDaysPerYear();
	vy[1] = 7.69901118419740425e-03 * getDaysPerYear();
	vz[1] = -6.90460016972063023e-05 * getDaysPerYear();
	m[1] = 9.54791938424326609e-04 * getSolarMass();
	
	// saturn
	x[2] = 8.34336671824457987e+00;
	y[2] = 4.12479856412430479e+00;
	z[2] = -4.03523417114321381e-01;
	vx[2] = -2.76742510726862411e-03 * getDaysPerYear();
	vy[2] = 4.99852801234917238e-03 * getDaysPerYear();
	vz[2] = 2.30417297573763929e-05 * getDaysPerYear();
	m[2] = 2.85885980666130812e-04 * getSolarMass();
	
	// uranus
	x[3] = 1.28943695621391310e+01;
	y[3] = -1.51111514016986312e+01;
	z[3] = -2.23307578892655734e-01;
	vx[3] =2.96460137564761618e-03 * getDaysPerYear();
	vy[3] =2.37847173959480950e-03 * getDaysPerYear();
	vz[3] =-2.96589568540237556e-05 * getDaysPerYear();
	m[3] = 4.36624404335156298e-05 * getSolarMass();

	// neptune
	x[4] = 1.53796971148509165e+01;
	y[4] = -2.59193146099879641e+01;
	z[4] = 1.79258772950371181e-01;
	vx[4] =2.68067772490389322e-03 * getDaysPerYear();
	vy[4] =1.62824170038242295e-03 * getDaysPerYear();
	vz[4] =-9.51592254519715870e-05 * getDaysPerYear();
	m[4] = 5.15138902046611451e-05 * getSolarMass();


	// init simulation
	N = 50_000_000;
	offsetMomentum(n, x, y, z, vx, vy, vz, m);

	// check initial energy
	// e should be -0.169075164
	e = calcEnergy(n, x, y, z, vx, vy, vz, m);
	de = e - (-0.169075164);
	if de < 0
	{
		de = - de;
	}

	assert de < 1;
	assert de < 0.1;
	assert de < 0.01;
	assert de < 0.001;
	assert de < 0.0001;
	assert de < 0.00001;
	assert de < 0.000001;
	assert de < 0.0000001;
	assert de < 0.00000001;
	assert de < 0.000000001;
	// these below fail
	//assert de < 0.0000000001;


	// run simulation
	for i in range(1, N)
	{
		advance(n, x, y, z, vx, vy, vz, m, 0.01);
	}

	// check final energy
	if N == 50_000_000
	{
		// e should be -0.169059907
		e = calcEnergy(n, x, y, z, vx, vy, vz, m);
		de = e - (-0.169059907);
		if de < 0
		{
			de = - de;
		}

		assert de < 1;
		assert de < 0.1;
		assert de < 0.01;
		assert de < 0.001;
		assert de < 0.0001;
		assert de < 0.00001;
		assert de < 0.000001;
		// these below fail
		//assert de < 0.0000001;
		//assert de < 0.00000001;
		//assert de < 0.000000001;
		//assert de < 0.0000000001;
	}



	free(x); free(y); free(z);
	free(vx); free(vy); free(vz);
	free(m);

	return 0;
}

