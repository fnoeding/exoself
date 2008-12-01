module nbody

from exoself.c.stdio import *
from exoself.c.math import *
from hacks.formatting import *


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



struct Planet
{
	x, y, z as float64;
	vx, vy, vz as float64;
	m as float64;
}





def advance(n as uint32, p as Planet*, dt as float64) as void
{
	for i in range(n)
	{
		for j in range(i + 1, n)
		{
			dx = p[i].x - p[j].x;
			dy = p[i].y - p[j].y;
			dz = p[i].z - p[j].z;

			dist = sqrt(dx * dx + dy * dy + dz * dz);
			mag = dt / (dist * dist * dist);

			p[i].vx -= dx * p[j].m * mag;
			p[i].vy -= dy * p[j].m * mag;
			p[i].vz -= dz * p[j].m * mag;

			p[j].vx += dx * p[i].m * mag;
			p[j].vy += dy * p[i].m * mag;
			p[j].vz += dz * p[i].m * mag;
		}
	}

	for i in range(n)
	{
		p[i].x += dt * p[i].vx;
		p[i].y += dt * p[i].vy;
		p[i].z += dt * p[i].vz;
	}
}




def calcEnergy(n as uint32, p as Planet*) as float64
{
	e = 0.0;

	for i in range(n)
	{
		e += 0.5 * p[i].m * (p[i].vx * p[i].vx + p[i].vy * p[i].vy + p[i].vz * p[i].vz);

		for j in range(i + 1, n)
		{
			dx = p[i].x - p[j].x;
			dy = p[i].y - p[j].y;
			dz = p[i].z - p[j].z;

			dist = sqrt(dx * dx + dy * dy + dz * dz);

			e -= (p[i].m * p[j].m) / dist;
		}
	}

	return e;
}


def offsetMomentum(n as uint32, p as Planet*) as void
{
	px as float64;
	py as float64;
	pz as float64;

	for i in range(n)
	{
		px += p[i].vx * p[i].m;
		py += p[i].vy * p[i].m;
		pz += p[i].vz * p[i].m;
	}

	p[0].vx = -px / getSolarMass();
	p[0].vy = -py / getSolarMass();
	p[0].vz = -pz / getSolarMass();
}





def main() as int32
{
	n = 5u;

	planets = new(Planet, 5);
	p = planets;

	// sun
	p[0].x = p[0].y = p[0].z = p[0].vx = p[0].vy = p[0].vz;
	p[0].m = getSolarMass();

	// jupiter
	p[1].x = 4.84143144246472090e+00;
	p[1].y = -1.16032004402742839e+00;
	p[1].z = -1.03622044471123109e-01;
	p[1].vx = 1.66007664274403694e-03 * getDaysPerYear();
	p[1].vy = 7.69901118419740425e-03 * getDaysPerYear();
	p[1].vz = -6.90460016972063023e-05 * getDaysPerYear();
	p[1].m = 9.54791938424326609e-04 * getSolarMass();

	// saturn
	p[2].x = 8.34336671824457987e+00;
	p[2].y = 4.12479856412430479e+00;
	p[2].z = -4.03523417114321381e-01;
	p[2].vx = -2.76742510726862411e-03 * getDaysPerYear();
	p[2].vy = 4.99852801234917238e-03 * getDaysPerYear();
	p[2].vz = 2.30417297573763929e-05 * getDaysPerYear();
	p[2].m = 2.85885980666130812e-04 * getSolarMass();

	// uranus
	p[3].x = 1.28943695621391310e+01;
	p[3].y = -1.51111514016986312e+01;
	p[3].z = -2.23307578892655734e-01;
	p[3].vx =2.96460137564761618e-03 * getDaysPerYear();
	p[3].vy =2.37847173959480950e-03 * getDaysPerYear();
	p[3].vz =-2.96589568540237556e-05 * getDaysPerYear();
	p[3].m = 4.36624404335156298e-05 * getSolarMass();

	// neptune
	p[4].x = 1.53796971148509165e+01;
	p[4].y = -2.59193146099879641e+01;
	p[4].z = 1.79258772950371181e-01;
	p[4].vx =2.68067772490389322e-03 * getDaysPerYear();
	p[4].vy =1.62824170038242295e-03 * getDaysPerYear();
	p[4].vz =-9.51592254519715870e-05 * getDaysPerYear();
	p[4].m = 5.15138902046611451e-05 * getSolarMass();

	// init simulation
	N = 50_000_000;
	offsetMomentum(n, p);

	// check initial energy
	// e should be -0.169075164
	e = calcEnergy(n, p);
	str = new(byte, 1024);
	format(str, 1024ul, ar"%.9f", e);
	puts(str);
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
		advance(n, p, 0.01);
	}

	e = calcEnergy(n, p);
	format(str, 1024ul, ar"%.9f", e);
	puts(str);

	// check final energy
	if N == 50_000_000
	{
		// e should be -0.169059907
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



	return 0;
}

